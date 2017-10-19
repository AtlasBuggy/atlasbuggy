import re
import time
import serial
from serial.tools import list_ports

from .generic import Generic
from .errors import *


class Arduino(Generic):
    ports = {}

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
    default_rates = [115200, 38400, 19200, 9600]
    buffer_pattern = re.compile("([^\r\n\t\x20-\x7e]|_)+")

    port_updates_per_second = 2000

    def __init__(self, whoiam, baud=115200, enabled=True, logger=None, *device_args, **device_kwargs):
        super(Arduino, self).__init__(enabled, logger)

        self.whoiam = whoiam  # ID tag of the microcontroller
        self.first_packet = None
        self.baud = baud
        if self.baud not in Arduino.default_rates:
            raise ValueError("Baud rate must be %s or %s. Supplied baud rate is %s" % (
                str(Arduino.default_rates[0:-1])[1:-1], str(Arduino.default_rates[-1]), self.baud))
        self.device = None
        self.device_args = device_args
        self.device_kwargs = device_kwargs

        self.protocol_packets = [Arduino.whoiam_header, Arduino.first_packet_header, Arduino.stop_packet_header]

    def list_addresses(self):
        com_ports = list_ports.comports()

        if len(com_ports) == 0:
            raise RuntimeError("No serial ports found!! "
                               "Try overriding this method with an alternative port finder or "
                               "install the correct drivers")

        addresses = []
        for port_no, description, address in com_ports:
            if 'USB' in address:
                self.logger.info("Found suitable address: '%s'" % port_no)
                addresses.append(port_no)

        return addresses

    def configure_device(self):
        device_port = None
        if len(Arduino.ports) == 0:
            addresses = self.list_addresses()
            if len(addresses) == 0:
                raise RuntimeError("Found no valid Arduino addresses!!")
            for address in addresses:
                for baud in self.default_rates:
                    self.logger.info("Polling address %s with baud %s" % (address, baud))
                    device_port = DevicePort(address, baud, self.device_args, self.device_kwargs, self.logger)
                    device_port.configure()

                    if device_port.is_arduino:
                        if self.whoiam == device_port.whoiam:
                            self.first_packet = device_port.first_packet
                            Arduino.ports[device_port.whoiam] = device_port
                        break

        if device_port is None:
            raise RuntimeError("Failed to find arduino device named %s" % self.whoiam)

        self.device = device_port

        self.logger.debug("device named %s started at %s" % (self.whoiam, self.device.start_time))
        self.device_read_queue.put((-self.device.start_time, self.first_packet))

    def poll_device(self):
        self.device.write(Arduino.start_packet)

        while self.device_active():
            time.sleep(1 / Arduino.port_updates_per_second)  # maintain a constant loop speed

            if not self.device.is_open():
                self.stop_device()
                raise DeviceClosedPrematurelyError("Serial port isn't open for some reason...")
            in_waiting = self.device.in_waiting()
            if in_waiting == 0:
                continue

            # read every possible character available and split them into packets
            packet_time, packets = self.device.read(in_waiting)
            if packets is None:  # if the read failed
                self.stop_device()
                raise DeviceReadPacketError("Failed to read packets", self)

            self.logger.debug("found %s packets at t=%s" % (len(packets), packet_time))

            # put data found into the queue
            for packet in packets:
                put_on_queue = True

                # check for protocol packet responses (responses to whoareyou, init?, start, stop)
                for header in self.protocol_packets:
                    if len(packet) >= len(header) and packet[:len(header)] == header:
                        # the Arduino can signal to stop if it sends "stopping"
                        if header == self.stop_packet_header:
                            self.stop_device()
                            raise DeviceClosedPrematurelyError(
                                "Port signalled to exit (stop flag was found)", self)
                        else:
                            self.logger.warning("Misplaced protocol packet:", repr(packet))
                        put_on_queue = False

                if put_on_queue:
                    self.device_read_queue.put((packet_time, packet))
                    # start_time isn't used. The main process has its own initial time reference

            while not self.device_write_queue.empty():
                packet = self.device_write_queue.get()
                self.device.write(packet)

        self.device.write(self.stop_packet)


class DevicePort:
    def __init__(self, address, baud, device_args, device_kwargs, logger):
        self.address = address
        self.baud = baud
        self.device_args = device_args
        self.device_kwargs = device_kwargs

        self.logger = logger

        self.is_arduino = False
        self.whoiam = ""
        self.first_packet = ""
        self.device = None
        self.start_time = None

        self.buffer = ''

    def configure(self):
        self.device = serial.Serial(self.address, self.baud, *self.device_args, **self.device_kwargs)
        # time.sleep(2)  # wait for microcontroller to wake up

        while self.in_waiting() < 0:
            time.sleep(0.001)

        self.whoiam = self.find_whoiam()
        if self.whoiam is not None:
            self.first_packet = self.find_first_packet()
            if self.first_packet is not None:
                self.is_arduino = True

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
                    raise RuntimeError("Serial read failed... Board never signalled ready")

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
            rounded_time = int((time.time() - start_time) * 10)
            if rounded_time > 5 and rounded_time % 3 == 0 and prev_rounded_time != rounded_time:
                attempts += 1
                self.logger.debug("Writing '%s' again" % ask_packet)
                self.write(Arduino.stop_packet)
                self.write(ask_packet)

            # return None if operation timed out
            if (time.time() - start_time) > Arduino.protocol_timeout:
                raise RuntimeError("Didn't receive response for packet '%s'. Operation timed out." % ask_packet)

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