import re
import time
import serial
import asyncio
from threading import Thread, Lock
from serial.tools import list_ports

from .generic import Generic
from .errors import *


class Arduino(Generic):
    # hello packet
    hello_response_header = "~hello!"

    # ready packet
    ready_response_header = "~ready!"

    # whoiam ID info
    whoiam_packet_ask = "~?"
    whoiam_response_header = "~iam"  # whoiam packets start with "~iam"

    # first packet info
    first_packet_ask = "~|"
    first_response_header = "~init:"

    stop_packet_ask = "~<"
    stop_response_header = "~stopping"

    start_packet_ask = "~>"

    time_response_header = "~ct:"

    # misc. device protocol
    protocol_timeout = 5  # seconds
    ready_protocol_timeout = 10
    packet_end = "\n"  # what this microcontroller's packets end with
    default_rate = 115200
    buffer_pattern = re.compile("([^\r\n\t\x20-\x7e]|_)+")

    port_updates_per_second = 100

    ports = {}
    table_lock = Lock()
    config_errors = []

    def __init__(self, whoiam, baud=115200, enabled=True, logger=None):
        super(Arduino, self).__init__(enabled, logger)

        self.whoiam = whoiam  # ID tag of the microcontroller
        self.baud = baud
        self.device_port = None

        self.start_time = 0.0
        self.first_packet = None

        # list of all protocol packets to be checked at the start
        self.init_protocol_packets = [Arduino.hello_response_header, Arduino.ready_response_header,
                                      Arduino.whoiam_response_header, Arduino.first_response_header,
                                      Arduino.stop_response_header]

        # all runtime protocol packets
        self.runtime_protocol_packets = [Arduino.time_response_header]

    @asyncio.coroutine
    def setup(self):
        self.configure_device()
        self.logger.info("%s's setup complete" % self.whoiam)

    def device_active(self):
        return not self.device_exit_event.is_set()

    @staticmethod
    def list_addresses():
        """Returns a list of valid possible Arduino USB serial addresses"""
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
        """Configure all devices if they haven't been already"""

        # Arduino.ports shared between all Arduino instances. Initialize it if it isn't
        if len(Arduino.ports) == 0:
            self.logger.info("configuring for the first time. whoiam=%s" % self.whoiam)

            addresses = Arduino.list_addresses()
            self.logger.info("Found suitable addresses: '%s'" % addresses)

            if len(addresses) == 0:
                raise RuntimeError("Found no valid Arduino addresses!!")

            # start threads that poll all discovered addresses
            Arduino.collect_all_devices(addresses, self.logger)

        self.logger.info("configuring done. Finding whoiam=%s" % self.whoiam)

        if self.whoiam not in Arduino.ports:
            raise RuntimeError("Failed to find arduino device named %s" % self.whoiam)

        # pull an initialized arduino from the ports dictionary and assign it to this instance of Arduino
        # matches whoiam ID's to the correct ports
        device_port_info = Arduino.ports[self.whoiam]
        device_port_info["logger"] = self.logger
        self.device_port = DevicePort.reinit(device_port_info)

        if self.device_port is None:
            raise RuntimeError("Failed to find arduino device named %s" % self.whoiam)

        self.first_packet = self.device_port.first_packet
        self.start_time = self.device_port.start_time

    @classmethod
    def collect_all_devices(cls, addresses, logger):
        """Initialize all Arduinos on their own threads"""

        tasks = []
        # initialize all discovered ports on its own thread
        for address in addresses:
            config_task = Thread(target=cls.configure_devices_task, args=(address, logger))
            tasks.append((address, config_task))
            config_task.start()

        # wait for all threads to finish
        for address, task in tasks:
            task.join()

        if len(cls.config_errors) > 0:
            raise RuntimeError(
                "The following errors occurred while configuring devices:\n%s" % (str(cls.config_errors)[1:-1])
            )

    @classmethod
    def configure_devices_task(cls, address, logger):
        """Threading task to initialize an address"""

        # Attempt to initialize the port. Don't throw an error. It will be handled later
        try:
            device_port = DevicePort.init_configure(address, logger)
        except BaseException as error:
            logger.warning(error)
            return

        # if initialized correctly, check for overlap otherwise add it to the ports dictionary
        if device_port.is_arduino:
            if device_port.whoiam in cls.ports:
                cls.config_errors.append("Address '%s' has the same whoiam ID (%s) as address '%s'" % (
                    device_port.address, device_port.whoiam, cls.ports[device_port.whoiam]["address"]))
                return

            port_info = dict(
                whoiam=device_port.whoiam, address=device_port.address,
                device=device_port.device,
                start_time=device_port.start_time, first_packet=device_port.first_packet
            )
            logger.info("address '%s' has ID '%s'" % (device_port.address, device_port.whoiam))

            cls.ports[device_port.whoiam] = port_info

    def poll_device(self):
        """Continuously poll from and send commands to the arduino until the exit signal is received"""

        self.device_port.write(Arduino.start_packet_ask + str(int(time.time())))

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

        current_pause_command = None

        # keep track of interesting packet stats. This method is on a separate process and these values should
        # not be accessed from outside this function.
        def update_packet_stats(num_packets_received):
            nonlocal notif_prev_time, notif_start_time, num_received, total_received, notif_interval
            num_received += num_packets_received
            total_received += num_packets_received
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

        self.logger.info("Device has started!")
        self.logger.info("init packet: %s" % self.first_packet)

        # the current buffer of information not push to the queue
        sequence_nums = []
        arduino_times = []
        packets = []

        while self.device_active():
            time.sleep(1 / Arduino.port_updates_per_second)  # maintain a constant loop speed

            if not self.device_port.is_open():
                self.stop_device()
                raise DeviceClosedPrematurelyError("Serial port isn't open for some reason...")

            # if the arduino has received data
            in_waiting = self.device_port.in_waiting()
            if in_waiting > 0:
                # get all possible data from the serial port
                packet_time = self.get_all_in_waiting(in_waiting, sequence_nums, arduino_times, packets)
                update_packet_stats(len(packets))

                # put to the queue differently depending on if more timestamps or packets were received
                if len(packets) > 0 or len(arduino_times) > 0:
                    # if more packets than timestamps were received, send less packets and wait for new timestamps
                    # to come in
                    if len(arduino_times) < len(packets):
                        self.device_read_queue.put((
                            packet_time,
                            tuple(sequence_nums),
                            tuple(arduino_times),
                            tuple(packets[:len(arduino_times)])
                        ))
                        packets = packets[len(arduino_times):]
                        sequence_nums = []
                        arduino_times = []
                    else:
                        # if more timestamps than packets were received, send less timestamps and wait for new packets
                        # to come in
                        self.device_read_queue.put((
                            packet_time,
                            tuple(sequence_nums[:len(packets)]),
                            tuple(arduino_times[:len(packets)]),
                            tuple(packets)
                        ))
                        sequence_nums = sequence_nums[len(packets):]
                        arduino_times = arduino_times[len(packets):]
                        packets = []

            # prevent the write queue from being accessed while sending commands
            with self.device_write_lock:
                # if the queue isn't currently paused,
                if current_pause_command is None:
                    # send all commands until it's empty
                    if not self.device_write_queue.empty():
                        while not self.device_write_queue.empty():
                            packet = self.device_write_queue.get()

                            # if the command is a pause command, start its timer and stop sending commands
                            if type(packet) == PauseCommand:
                                current_pause_command = packet
                                current_pause_command.start()
                                break
                            else:
                                self.device_port.write(packet)
                # if the pause command is over, reset current_pause_command
                elif current_pause_command.expired():
                    self.logger.debug("Timer started at %s expired" % current_pause_command.start_time)
                    current_pause_command = None

        # tell the arduino to stop when finished
        self.device_port.write(self.stop_packet_ask)

        self.logger.info("Closing down device port")
        self.device_port.device.close()

        self.logger.info("Device process stopped")

    def get_all_in_waiting(self, in_waiting, sequence_nums, arduino_times, packets):
        """
        Read every possible character available and split them into packets.
        Append new values to the supplied list pointers "sequence_nums", arduino_times", and "packets"
        """

        packet_time, new_packets = self.device_port.read(in_waiting)
        if new_packets is None:  # if the read failed
            self.stop_device()
            raise DeviceReadPacketError("Failed to read packets", self)

        if len(new_packets) > 0:
            for packet in new_packets:
                # check if a packet is a timestamp protocol packet
                if not self._check_for_time_packet(packet, sequence_nums, arduino_times):

                    # filter out packets with initialization protocol headers
                    # indicates the arduino is behaving eradically or that it wants to stop
                    if self._filter_packet(packet):
                        packets.append(packet)

        return packet_time

    def _check_for_time_packet(self, packet, sequence_nums, arduino_times):
        """Check if the packet matches the timestamp header. Parse the values."""

        if len(packet) >= len(Arduino.time_response_header) and \
                        packet[:len(Arduino.time_response_header)] == Arduino.time_response_header:
            if Arduino.time_response_header == self.time_response_header:
                data = packet[len(Arduino.time_response_header):]
                overflow, timer, sequence_num_part1, sequence_num_part2 = data.split(":")
                sequence_num = ((int(sequence_num_part1) << 32) | int(sequence_num_part2))
                arduino_time = ((int(overflow) << 32) | int(timer)) / 1E6

                sequence_nums.append(sequence_num)
                arduino_times.append(arduino_time)

                return True
        return False

    def _filter_packet(self, packet):
        """Check for misplaced init protocol packet responses (responses to whoareyou, init?, start, stop)"""

        for header in self.init_protocol_packets:
            if len(packet) >= len(header) and packet[:len(header)] == header:
                # the Arduino can signal to stop if it sends "stopping"
                if header == self.stop_response_header:
                    self.stop_device()
                    raise DeviceClosedPrematurelyError(
                        "Port signalled to exit (stop flag was found)", self)
                else:
                    self.logger.warning("Misplaced protocol packet: %s" % repr(packet))
                return False

        return True

    def pause_command(self, pause_time, relative_time=True):
        """
        Send a pause command. This prevents commands from being sent for "pause_time" seconds.
        If relative_time is False, pause_time is the unix timestamp that write will be unfrozen at.
        """
        with self.device_write_lock:
            self.device_write_queue.put(PauseCommand(pause_time, relative_time))
            if relative_time:
                self.log_to_buffer(time.time(), "pausing for %ss" % pause_time)
            else:
                self.log_to_buffer(time.time(), "pausing until %s" % pause_time)

    def cancel_commands(self):
        """
        Cancel all commands on the queue. 
        If there is current a pause, the pause won't be cancelled until the timer expires.
        """
        with self.device_write_lock:
            self.logger.debug("cancelling all commands")
            while not self.device_write_queue.empty():
                self.logger.debug("cancelling '%s'" % self.device_write_queue.get())


class PauseCommand:
    """struct holding a pause command telling the command queue to pause for some time"""
    def __init__(self, pause_time, relative_time):
        self.pause_time = pause_time
        self.start_time = 0.0
        self.relative_time = relative_time

    def start(self):
        self.start_time = time.time()

    def expired(self):
        if self.relative_time:
            return time.time() - self.start_time > self.pause_time
        else:
            return time.time() > self.pause_time


class DevicePort:
    def __init__(self, address, logger, device=None, start_time=None, first_packet="", whoiam=""):
        """
        Wraps the serial.Serial class and implements the atlasbuggy serial protocol for arduinos 
        
        :param address: USB serial address string
        :param logger: logger instance for debugging
        :param device: an instance of serial.Serial
        :param start_time: device unix timestamp start time
        :param first_packet: initialization data sent by the arduino at the start
        :param whoiam: whoiam ID indicating which Arduino class should be matched to which serial port
        """
        self.address = address

        self.logger = logger

        self.is_arduino = False  # will become True if all protocol initialization checks pass
        self.device = device
        self.start_time = start_time
        self.first_packet = first_packet
        self.whoiam = whoiam

        self.buffer = ''  # current packet buffer

    @classmethod
    def init_configure(cls, address, logger):
        """
        Initialize a device port for the configuration phase.
        Self assigns whoiam and first_packet.
        """
        device_port = DevicePort(address, logger)
        device_port.configure()

        return device_port

    def configure(self):
        self.device = serial.Serial(self.address, Arduino.default_rate)

        # wait for the device to send data
        check_time = time.time()
        while self.in_waiting() < 0:
            time.sleep(0.001)

            if time.time() - check_time > Arduino.protocol_timeout:
                self.logger.info(
                    "Waited for '%s' for %ss with no response..." % (self.address, Arduino.protocol_timeout)
                )
                return
        self.logger.debug("%s is ready" % self.address)
        time.sleep(2)  # wait for the device to boot

        # find the following protocols in order:
        # hello, ready, whoiam, first_packet
        # if all are found, the arduino device is ready to proceed
        if self.find_hello():
            if self.find_ready():
                self.whoiam = self.find_whoiam()

                if self.whoiam is not None:
                    self.first_packet = self.find_first_packet()

                    if self.first_packet is not None:
                        self.is_arduino = True

    @classmethod
    def reinit(cls, kwargs):
        """Reinitialize a device port. All ports are configured at this point. Use supplied constructor values."""
        return DevicePort(**kwargs)

    def find_hello(self):
        """
        The first packet sent by the arduino is "~hello!"
        This signals the ardunio is initializing
        """

        hello_packet = self.check_protocol("", Arduino.hello_response_header)
        if hello_packet:
            self.logger.debug("'%s' never sent hello!" % self.address)
        else:
            self.logger.debug("'%s' said hello!" % self.address)

        return hello_packet is not None

    def find_ready(self):
        """
        The first packet sent by the arduino is "~hello!"
        This signals the ardunio is initializing
        """

        ready_packet = self.check_protocol("", Arduino.ready_response_header, Arduino.ready_protocol_timeout)
        if ready_packet is None:
            self.logger.debug("'%s' never sent ready!" % self.address)
        else:
            self.logger.debug("'%s' said ready!" % self.address)

        return ready_packet is not None

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

        whoiam = self.check_protocol(Arduino.whoiam_packet_ask, Arduino.whoiam_response_header)

        if whoiam is None:
            self.logger.debug("Failed to obtain whoiam ID from '%s'!" % self.address)
        else:
            self.logger.debug("Found ID '%s' at address '%s'" % (whoiam, self.address))

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
        first_packet = self.check_protocol(Arduino.first_packet_ask, Arduino.first_response_header)

        if first_packet is None:
            self.logger.debug("Failed to obtain first packet from '%s'!" % self.address)
        else:
            self.logger.debug("Received initialization data from %s: %s" % (repr(first_packet), self.address))

        return first_packet

    def check_protocol(self, ask_packet, recv_packet_header, protocol_timeout=None):
        """
        A call and response method. After an "ask packet" is sent, the process waits for
        a packet with the expected header for 2 seconds

        For initialization

        :param ask_packet: packet to send
        :param recv_packet_header: what the received packet should start with
        :return: the packet received with the header and packet end removed
        """

        if protocol_timeout is None:
            protocol_timeout = Arduino.protocol_timeout

        if ask_packet:
            self.logger.debug("Checking '%s' protocol at '%s'" % (ask_packet, self.address))
            self.write(ask_packet)
        else:
            self.logger.debug("Checking '%s' protocol at '%s'" % (recv_packet_header, self.address))

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

                packet_time, packet = self.readline()
                self.logger.debug("Got packet: %s from '%s'" % (repr(packet), self.address))
                if packet is None:
                    return None

                # return None if read failed
                if packet is None:
                    raise RuntimeError(
                        "Serial read failed for address '%s'... Board never signalled ready" % self.address)

                # if len(packets) > 0 and self.start_time is None:

                # parse received packet
                if len(packet) == 0:
                    self.logger.debug("Empty packet from '%s'! Contained only \\n" % self.address)
                    continue
                if packet[0:len(recv_packet_header)] == recv_packet_header:  # if the packet starts with the header,
                    self.logger.debug("received packet: %s from '%s'" % (repr(packet), self.address))

                    answer_packet = packet[len(recv_packet_header):]  # record it and return it

                    abides_protocol = True

            prev_rounded_time = rounded_time
            rounded_time = int((time.time() - start_time) * 5)
            if rounded_time > protocol_timeout and rounded_time % 3 == 0 and prev_rounded_time != rounded_time:
                attempts += 1
                if ask_packet:
                    self.logger.debug("Writing '%s' again to '%s'" % (ask_packet, self.address))
                else:
                    self.logger.debug("Still waiting for '%s' packet from '%s'" % (recv_packet_header, self.address))

                self.write(Arduino.stop_packet_ask)
                if ask_packet:
                    self.write(ask_packet)

            # return None if operation timed out
            if (time.time() - start_time) > protocol_timeout:
                if ask_packet:
                    raise RuntimeError(
                        "Didn't receive response for packet '%s' on address '%s'. "
                        "Operation timed out after %ss." % (
                            ask_packet, self.address, protocol_timeout))
                else:
                    raise RuntimeError(
                        "Didn't receive response waiting for packet '%s' on address '%s'. "
                        "Operation timed out after %ss" % (
                            recv_packet_header, self.address, protocol_timeout))

        return answer_packet  # when the while loop exits, abides_protocol must be True

    def write(self, packet):
        """Write a string. "packet" should not have a new line in it. This is sent for you."""
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
        """Wrap isOpen for the Arduino class"""
        return self.device.isOpen()

    def readline(self):
        """
        Read until the next new line character

        For initialization use.
        """
        packet_time = time.time()
        if self.device.isOpen():
            incoming = self.device.readline()
        else:
            raise RuntimeError("Serial port wasn't open for reading...")

        if len(incoming) > 0:
            # append to the buffer
            try:
                packet = incoming.decode("utf-8", "ignore")
                return packet_time, packet[:-1]  # remove \n
            except UnicodeDecodeError:
                self.logger.debug("Found non-ascii characters! '%s'" % incoming)
                raise
        else:
            return packet_time, None

    def read(self, in_waiting):
        """
        Read all available data on serial and split them into packets as
        indicated by packet_end.

        For initialization and process use
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

            # -- redacted --, any characters can be send. You parse it how you like.
            # apply a regex pattern to remove invalid characters
            # buf = Arduino.buffer_pattern.sub('', self.buffer)
            # if len(self.buffer) != len(buf):
            #     self.logger.debug("Invalid characters found: %s" % repr(self.buffer))
            # self.buffer = buf

            if len(self.buffer) > len(Arduino.packet_end):
                # split based on user defined packet end
                packets = self.buffer.split(Arduino.packet_end)

                # reset the buffer. If the buffer ends with \n, the last element in packets will be an empty string
                self.buffer = packets.pop(-1)

                return packet_time, packets
        return packet_time, []
