import re
import time
import serial
import asyncio
from threading import Thread, Lock
from serial.tools import list_ports

from .generic import Generic
from .errors import *


class Arduino(Generic):
    # whoiam ID info
    whoiam_header = "iam"  # whoiam packets start with "iam"
    whoiam_ask = "whoareyou"

    # first packet info
    first_packet_ask = "init?"
    first_packet_header = "init:"

    stop_packet = "stop"
    stop_packet_header = "stopping"

    start_packet = "start"

    # misc. device protocol
    protocol_timeout = 3  # seconds
    packet_end = "\n"  # what this microcontroller's packets end with
    default_rate = 115200
    buffer_pattern = re.compile("([^\r\n\t\x20-\x7e]|_)+")

    port_updates_per_second = 100

    ports = {}
    table_lock = Lock()
    config_errors = []

    def __init__(self, whoiam, baud=115200, enabled=True, logger=None, *device_args, **device_kwargs):
        super(Arduino, self).__init__(enabled, logger)

        self.whoiam = whoiam  # ID tag of the microcontroller
        self.baud = baud
        self.device_port = None
        self.device_args = device_args
        self.device_kwargs = device_kwargs

        self.start_time = 0.0
        self.first_packet = None

        self.protocol_packets = [Arduino.whoiam_header, Arduino.first_packet_header, Arduino.stop_packet_header]

        self.configure_device()

    @staticmethod
    def list_addresses():
        com_ports = list_ports.comports()

        if len(com_ports) == 0:
            raise RuntimeError("No serial ports found!! "
                               "Try overriding this method with an alternative port finder or "
                               "install the correct drivers")

        addresses = []
        for port_no, description, address in com_ports:
            if 'USB' in address:
                addresses.append(port_no)

        return addresses

    def configure_device(self):
        if len(Arduino.ports) == 0:
            self.logger.info("configuring for the first time. whoiam=%s" % self.whoiam)

            addresses = Arduino.list_addresses()
            self.logger.info("Found suitable addresses: '%s'" % addresses)

            if len(addresses) == 0:
                raise RuntimeError("Found no valid Arduino addresses!!")

            Arduino.collect_all_devices(addresses, self.logger, *self.device_args, **self.device_kwargs)

        self.logger.info("configuring done. Finding whoiam=%s" % self.whoiam)

        device_port_info = Arduino.ports[self.whoiam]
        device_port_info["logger"] = self.logger
        self.device_port = DevicePort.reinit(device_port_info)

        if self.device_port is None:
            raise RuntimeError("Failed to find arduino device named %s" % self.whoiam)

        self.first_packet = self.device_port.first_packet
        self.start_time = self.device_port.start_time

    @classmethod
    def collect_all_devices(cls, addresses, logger, *device_args, **device_kwargs):
        tasks = []
        for address in addresses:
            config_task = Thread(target=cls.configure_devices_task, args=(address, device_args, device_kwargs, logger))
            tasks.append((address, config_task))
            config_task.start()

        for address, task in tasks:
            task.join()

        if len(cls.config_errors) > 0:
            raise RuntimeError(
                "The following errors occurred while configuring devices:\n%s" % (str(cls.config_errors)[1:-1])
            )

    @classmethod
    def configure_devices_task(cls, address, device_args, device_kwargs, logger):
        try:
            device_port = DevicePort.init_configure(
                address, device_args, device_kwargs, logger
            )
        except BaseException as error:
            logger.warning(error)
            return

        if device_port.is_arduino:
            if device_port.whoiam in cls.ports:
                cls.config_errors.append("Address '%s' has the same whoiam ID (%s) as address '%s'" % (
                    device_port.address, device_port.whoiam, cls.ports[device_port.whoiam]["address"]))
                return

            port_info = dict(
                whoiam=device_port.whoiam, address=device_port.address,
                device_args=device_port.device_args,
                device_kwargs=device_port.device_kwargs, device=device_port.device,
                start_time=device_port.start_time, first_packet=device_port.first_packet
            )
            logger.info("address '%s' has ID '%s'" % (device_port.address, device_port.whoiam))

            cls.ports[device_port.whoiam] = port_info

    def poll_device(self):
        self.device_port.write(Arduino.start_packet)

        if self.baud != Arduino.default_rate:
            time.sleep(0.01)  # wait for start packet to process
            self.device_port.device.baudrate = self.baud
            self.logger.info("Device named '%s' at '%s' is now at baud rate '%s'" % (
                self.device_port.whoiam, self.device_port.address, self.baud))

        notif_prev_time = time.time()
        notif_start_time = time.time()
        num_received = 0
        total_received = 0
        notif_interval = 3

        self.logger.info("Device has started!")

        while self.device_active():
            time.sleep(1 / Arduino.port_updates_per_second)  # maintain a constant loop speed

            if not self.device_port.is_open():
                self.stop_device()
                raise DeviceClosedPrematurelyError("Serial port isn't open for some reason...")
            in_waiting = self.device_port.in_waiting()
            if in_waiting == 0:
                continue

            # read every possible character available and split them into packets
            packet_time, packets = self.device_port.read(in_waiting)
            if packets is None:  # if the read failed
                self.stop_device()
                raise DeviceReadPacketError("Failed to read packets", self)

            if len(packets) > 0:
                num_received += len(packets)
                total_received += len(packets)
                current_time = time.time()
                if current_time - notif_prev_time > notif_interval:
                    self.logger.info(
                        "found %s packets in %ss (avg=%0.1f packets/sec). "
                        "%s received in total (avg=%0.1f packets/sec)" % (
                            num_received,
                            notif_interval,
                            num_received / notif_interval,
                            total_received,
                            total_received / (current_time - notif_start_time))
                    )
                    num_received = 0
                    notif_prev_time = current_time

                packets[:] = [packet for packet in packets if
                              self.filter_packet(packet)]  # filters and modifies the packets buffer
                self.device_read_queue.put((packet_time, packets))

            if not self.device_write_queue.empty():
                self.logger.debug("Write queue not empty")
            while not self.device_write_queue.empty():
                packet = self.device_write_queue.get()
                self.device_port.write(packet)

        self.device_port.write(self.stop_packet)

    def filter_packet(self, packet):
        # check for protocol packet responses (responses to whoareyou, init?, start, stop)
        for header in self.protocol_packets:
            if len(packet) >= len(header) and packet[:len(header)] == header:
                # the Arduino can signal to stop if it sends "stopping"
                if header == self.stop_packet_header:
                    self.stop_device()
                    raise DeviceClosedPrematurelyError(
                        "Port signalled to exit (stop flag was found)", self)
                else:
                    self.logger.warning("Misplaced protocol packet: %s" % repr(packet))
                return False
        return True

    def read(self):
        return self.device_read_queue.get()

    def empty(self):
        return self.device_read_queue.empty()

    def write(self, packet):
        self.device_write_queue.put(packet)

    @asyncio.coroutine
    def teardown(self):
        yield from super(Arduino, self).teardown()
        self.device_port.device.close()


class DevicePort:
    def __init__(self, address, device_args, device_kwargs, logger, device=None, start_time=None,
                 first_packet="", whoiam=""):
        self.address = address
        self.device_args = device_args
        self.device_kwargs = device_kwargs

        self.logger = logger

        self.is_arduino = False
        self.whoiam = whoiam
        self.first_packet = first_packet
        self.device = device
        self.start_time = start_time

        self.buffer = ''

    @classmethod
    def init_configure(cls, address, device_args, device_kwargs, logger):
        device_port = DevicePort(address, device_args, device_kwargs, logger)
        device_port.configure()

        return device_port

    def configure(self):
        self.device = serial.Serial(self.address, Arduino.default_rate, *self.device_args, **self.device_kwargs)

        # wait for device to wake up:
        check_time = time.time()
        while self.in_waiting() < 0:
            time.sleep(0.001)

            if time.time() - check_time > Arduino.protocol_timeout:
                self.logger.info(
                    "Waited for '%s' for %ss with no response..." % (self.address, Arduino.protocol_timeout)
                )
                return
        self.logger.debug("%s is ready" % self.address)
        time.sleep(1.59)  # wait for the device to boot (found by minimizing time difference of arduino and computer)

        self.whoiam = self.find_whoiam()
        if self.whoiam is not None:
            self.first_packet = self.find_first_packet()
            if self.first_packet is not None:
                self.is_arduino = True

    @classmethod
    def reinit(cls, kwargs):
        return DevicePort(**kwargs)

    def find_whoiam(self):
        """
        Get the whoiam packet from the microcontroller. This method will wait 1 second for a packet before
        throwing a timeout error.

        example:
            sent: "whoareyou\n"
            received: "iamlidar\n"

            The whoiam ID for this object is 'lidar'

        For initialization
        """

        whoiam = self.check_protocol(Arduino.whoiam_ask, Arduino.whoiam_header)

        if whoiam is None:
            self.logger.debug("Failed to obtain whoiam ID!")
        else:
            self.logger.debug("Found ID '%s'" % whoiam)

        return whoiam

    def find_first_packet(self):
        """
        Get the first packet from the microcontroller. This method will wait 1 second for a packet before
        throwing a timeout error.

        example:
            sent: "init?\n"
            received: "init:\n" (if nothing to init, initialization methods not called)
            received: "init:something interesting\t01\t23\n"
                'something interesting\t01\t23' would be the first packet

        For initialization
        """
        first_packet = self.check_protocol(Arduino.first_packet_ask, Arduino.first_packet_header)

        if first_packet is None:
            self.logger.debug("Failed to obtain first packet!")
        else:
            self.logger.debug("sent initialization data: %s" % repr(first_packet))

        return first_packet

    def check_protocol(self, ask_packet, recv_packet_header):
        """
        A call and response method. After an "ask packet" is sent, the process waits for
        a packet with the expected header for 2 seconds

        For initialization

        :param ask_packet: packet to send
        :param recv_packet_header: what the received packet should start with
        :return: the packet received with the header and packet end removed
        """
        self.logger.debug("Checking '%s' protocol" % ask_packet)

        self.write(ask_packet)

        start_time = time.time()
        abides_protocol = False
        answer_packet = None
        attempts = 0
        rounded_time = 0

        # wait for the correct response
        while not abides_protocol:
            in_waiting = self.in_waiting()
            if in_waiting > 0:
                if self.start_time is None:
                    self.start_time = time.time()

                packet_time, packets = self.read(in_waiting)
                if packets is None:
                    return None

                # return None if read failed
                if packets is None:
                    raise RuntimeError(
                        "Serial read failed for address '%s'... Board never signalled ready" % self.address)

                # if len(packets) > 0 and self.start_time is None:

                # parse received packets
                for packet in packets:
                    if len(packet) == 0:
                        self.logger.debug("Empty packet! Contained only \\n")
                        continue
                    if packet[0:len(recv_packet_header)] == recv_packet_header:  # if the packet starts with the header,
                        self.logger.debug("received packet: %s" % repr(packet))

                        answer_packet = packet[len(recv_packet_header):]  # record it and return it

                        abides_protocol = True

            prev_rounded_time = rounded_time
            rounded_time = int((time.time() - start_time) * 5)
            if rounded_time > Arduino.protocol_timeout and rounded_time % 3 == 0 and prev_rounded_time != rounded_time:
                attempts += 1
                self.logger.debug("Writing '%s' again" % ask_packet)
                self.write(Arduino.stop_packet)
                self.write(ask_packet)

            # return None if operation timed out
            if (time.time() - start_time) > Arduino.protocol_timeout:
                raise RuntimeError("Didn't receive response for packet '%s' on address '%s'. Operation timed out." % (
                    ask_packet, self.address))

        return answer_packet  # when the while loop exits, abides_protocol must be True

    def write(self, packet):
        data = bytearray(str(packet) + Arduino.packet_end, 'ascii')
        self.device.write(data)

    def in_waiting(self):
        """
        Safely check the serial buffer.
        :return: None if an OSError occurred, otherwise an integer value indicating the buffer size 
        """
        try:
            return self.device.inWaiting()
        except OSError:
            self.logger.error("Failed to check serial. Is there a loose connection?")
            raise

    def is_open(self):
        return self.device.isOpen()

    def read(self, in_waiting):
        """
        Read all available data on serial and split them into packets as
        indicated by packet_end.

        For initialization and process use

        :return: None indicates the serial read failed and that the main thread should be stopped.
            Returns the received packets otherwise
        """
        # read every available character
        packet_time = time.time()
        if self.device.isOpen():
            incoming = self.device.read(in_waiting)
        else:
            raise RuntimeError("Serial port wasn't open for reading...")

        if len(incoming) > 0:
            # append to the buffer
            try:
                self.buffer += incoming.decode("utf-8", "ignore")
            except UnicodeDecodeError:
                self.logger.debug("Found non-ascii characters! '%s'" % incoming)
                raise

                # apply a regex pattern to remove invalid characters
            buf = Arduino.buffer_pattern.sub('', self.buffer)
            if len(self.buffer) != len(buf):
                self.logger.debug("Invalid characters found:", repr(self.buffer))
            self.buffer = buf

            if len(self.buffer) > len(Arduino.packet_end):
                # split based on user defined packet end
                packets = self.buffer.split(Arduino.packet_end)

                # reset the buffer. If the buffer ends with \n, the last element in packets will be an empty string
                self.buffer = packets.pop(-1)

                return packet_time, packets
        return packet_time, []
