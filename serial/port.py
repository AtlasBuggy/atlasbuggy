"""
SerialPorts are the direct interface between serial port objects and microcontrollers.
Each port runs on its own process. The whoiam ID of the port is found at runtime. The
corresponding SerialObject is paired in SerialStream.
"""

import re
import time
import traceback
from multiprocessing import Event, Lock, Process, Queue, Value

import serial.tools.list_ports
from serial.serialutil import SerialException

import serial
from ..clock import Clock
from ..serial.errors import *


class SerialPort(Process):
    """
    A multiprocessing based wrapper for an instance of pyserial's Serial.
    A SerialStream class manages all instances of this class.
    This class is for internal use only
    """

    port_updates_per_second = 1000

    def __init__(self, port_address):
        """
        :param port_address: Address to use when starting up the port
        """

        self.address = port_address

        self.packet_queue = Queue()
        self.counter = Value('i', 0)
        self.lock = Lock()
        self.queue_len = 0

        # status variables
        self.configured = True
        self.abides_protocols = True
        self.port_assigned = False

        self.message_lock = Lock()
        self.error_message = Queue()

        self.print_out_lock = Lock()
        self.debug_print_outs = Queue()

        # time variables
        self.start_time = 0.0
        self.loop_time = 0.0

        # whoiam ID info
        self.whoiam = None  # ID tag of the microcontroller
        self.whoiam_header = "iam"  # whoiam packets start with "iam"
        self.whoiam_ask = "whoareyou"

        # first packet info
        self.first_packet = None
        self.first_packet_ask = "init?"
        self.first_packet_header = "init:"

        self.stop_packet_ask = "stop"
        self.stop_packet_header = "stopping"

        self.protocol_timeout = 3  # seconds
        self.protocol_packets = [self.whoiam_header, self.first_packet_header, self.stop_packet_header]

        # misc. serial protocol
        self.packet_end = "\n"  # what this microcontroller's packets end with
        self.default_rate = 115200
        self.baud_rate = Value('i', self.default_rate)

        # buffer for putting packets into
        self.buffer = ""
        self.prev_read_packets = []
        self.prev_write_packet = ""

        # leaves tabs, letters, numbers, spaces, newlines, and carriage returns
        self.buffer_pattern = re.compile("([^\r\n\t\x20-\x7e]|_)+")

        # events and locks
        self.exit_event_lock = Lock()
        self.start_event_lock = Lock()

        self.exit_event = Event()
        self.start_event = Event()
        self.stop_event = Event()

        self.serial_lock = Lock()

        self.serial_ref = None

        super(SerialPort, self).__init__(target=self.update)

    # ----- initialization methods -----

    def initialize(self):
        """
        Run through start up protocols. Find the whoiam ID and retrieve find packets. 
        """

        # attempt to open the serial port
        try:
            self.serial_ref = serial.Serial(port=self.address, baudrate=self.baud_rate.value)
        except SerialException as error:
            self.handle_error(error, traceback.format_stack())
            self.configured = False

        time.sleep(2)  # wait for microcontroller to wake up

        if self.configured:
            # Find the ID of this port. The ports will be matched up to the correct RobotObject later
            self.find_whoiam()
            if self.whoiam is not None:
                self.find_first_packet()
            else:
                self.debug_print("whoiam ID was None, skipping find_first_packet")
        else:
            self.debug_print("Port not configured. Skipping find_whoiam")

    def send_start(self):
        """
        Send the start flag
        For external use
        :return: True if successful
        """
        self.debug_print("sending start")
        return self.write_packet("start")

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

        self.whoiam = self.check_protocol(self.whoiam_ask, self.whoiam_header)

        if self.whoiam is not None:
            self.debug_print("%s has ID '%s'" % (self.address, self.whoiam))
        else:
            # self.configured = False
            self.abides_protocols = False
            self.debug_print("Failed to obtain whoiam ID!")

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
        self.first_packet = self.check_protocol(self.first_packet_ask, self.first_packet_header)

        if self.first_packet is not None:
            self.debug_print("sent initialization data: %s" % repr(self.first_packet))
        else:
            # self.configured = False
            self.abides_protocols = False
            self.debug_print("Failed to obtain first packet!")

    def check_protocol(self, ask_packet, recv_packet_header):
        """
        A call and response method. After an "ask packet" is sent, the process waits for
        a packet with the expected header for 2 seconds

        For initialization

        :param ask_packet: packet to send
        :param recv_packet_header: what the received packet should start with
        :return: the packet received with the header and packet end removed
        """
        self.debug_print("Checking '%s' protocol" % ask_packet)

        if not self.write_packet(ask_packet):
            return None  # return None if write failed

        start_time = time.time()
        abides_protocol = False
        answer_packet = ""
        attempts = 0
        rounded_time = 0

        # wait for the correct response
        while not abides_protocol:
            in_waiting = self.in_waiting()
            if in_waiting > 0:
                packets = self.read_packets(in_waiting)
                if packets is None:
                    return None
                self.print_packets(packets)

                # return None if read failed
                if packets is None:
                    self.handle_error("Serial read failed... Board never signalled ready", traceback.format_stack())
                    return None

                # parse received packets
                for packet in packets:
                    if len(packet) == 0:
                        self.debug_print("Empty packet! Contained only \\n")
                        continue
                    if packet[0:len(recv_packet_header)] == recv_packet_header:  # if the packet starts with the header,
                        self.debug_print("received packet: " + repr(packet))

                        answer_packet = packet[len(recv_packet_header):]  # record it and return it

                        abides_protocol = True

            prev_rounded_time = rounded_time
            rounded_time = int((time.time() - start_time) * 10)
            if rounded_time > 5 and rounded_time % 3 == 0 and prev_rounded_time != rounded_time:
                attempts += 1
                self.debug_print("Writing '%s' again" % ask_packet)
                if not self.write_packet(ask_packet):
                    return None

            # return None if operation timed out
            if (time.time() - start_time) > self.protocol_timeout:
                self.handle_error("Didn't receive response for packet '%s'. Operation timed out." % ask_packet,
                                  traceback.format_stack())
                return None

        return answer_packet  # when the while loop exits, abides_protocol must be True

    def handle_error(self, error, stack_trace):
        """
        When errors occur in a SerialPort, the process doesn't crash. The error is recorded,
        self.update is stopped, and the main process is notified so all other ports can close safely

        For initialization and process use

        :param error: The error message to record
        """
        with self.exit_event_lock:
            self.exit_event.set()

        # if self.error_message.empty():
        full_message = ""
        for line in stack_trace:
            full_message += str(line)

        if type(error) == str:
            full_message += error
        else:
            full_message += "%s: %s\n" % (error.__class__.__name__, str(error))

        full_message += "Previous read: %s, write: %s" % (self.prev_read_packets, self.prev_write_packet)

        with self.message_lock:
            # queue will always be size of one. Easiest way to share strings and avoid race conditions.
            # (sometimes the error message would have arrived incomplete because
            # it gets printed before it gets formed...)
            self.error_message.put(full_message)

    # ----- run methods -----

    def update(self):
        """
        Called when SerialPort.start is called. Continuously checks the serial port for new data.
        """

        self.start_time = time.time()
        clock = Clock(SerialPort.port_updates_per_second)
        clock.start(self.start_time)

        time.sleep(0.01)  # Wait a brief time before starting and changing the baud rate

        with self.baud_rate.get_lock():
            if self.baud_rate.value != self.default_rate:  # if changed externally
                self.serial_ref.baudrate = self.baud_rate.value
                self.debug_print("Baud is now", self.serial_ref.baudrate)
            else:
                self.debug_print("Baud rate unchanged")

        with self.start_event_lock:
            self.start_event.set()

        try:
            while True:
                # break if exit flag is set
                with self.exit_event_lock:
                    if self.exit_event.is_set():
                        break

                with self.serial_lock:
                    # close the process if the serial port isn't open
                    if not self.serial_ref.isOpen():
                        self.stop()
                        raise RobotSerialPortClosedPrematurelyError("Serial port isn't open for some reason...", self)

                    in_waiting = self.in_waiting()

                    if in_waiting is None:
                        # caught an OSError. Likely the cable came loose
                        self.stop()
                        raise RobotSerialPortClosedPrematurelyError(
                            "Failed to check serial. Is there a loose connection?", self)
                    elif in_waiting > 0:
                        # read every possible character available and split them into packets
                        packets = self.read_packets(in_waiting)
                        if packets is None:  # if the read failed
                            self.stop()
                            raise RobotSerialPortReadPacketError("Failed to read packets", self)

                        # put data found into the queue
                        with self.lock:
                            for packet in packets:
                                put_on_queue = True

                                # check for protocol packet responses (responses to whoareyou, init?, start, stop)
                                for header in self.protocol_packets:
                                    if len(packet) >= len(header) and packet[:len(header)] == header:

                                        # the Arduino can signal to stop if it sends "stopping"
                                        if header == self.stop_packet_header:
                                            self.stop()
                                            raise RobotSerialPortClosedPrematurelyError(
                                                "Port signalled to exit (stop flag was found)", self)
                                        else:
                                            self.debug_print("Misplaced protocol packet:", repr(packet))
                                        put_on_queue = False
                                if put_on_queue:
                                    self.packet_queue.put((time.time(), packet))
                                    # start_time isn't used. The main process has its own initial time reference

                            self.counter.value += len(packets)

                clock.update()  # maintain a constant loop speed
        except KeyboardInterrupt:
            self.debug_print("KeyboardInterrupt in port loop")

        self.debug_print("Current buffer:", repr(self.buffer))
        self.debug_print("While loop exited. Exit event triggered.")

        if not self.send_stop_events():
            self.handle_error("Stop flag failed to send!", traceback.format_stack())

    def in_waiting(self):
        """
        Safely check the serial buffer.
        :return: None if an OSError occurred, otherwise an integer value indicating the buffer size 
        """
        try:
            return self.serial_ref.inWaiting()
        except OSError as error:
            self.debug_print("Failed to check serial. Is there a loose connection?")
            self.handle_error(error, traceback.format_stack())
            return None

    def read_packets(self, in_waiting):
        """
        Read all available data on serial and split them into packets as
        indicated by packet_end.

        For initialization and process use

        :return: None indicates the serial read failed and that the main thread should be stopped.
            Returns the received packets otherwise
        """
        try:
            # read every available character
            if self.serial_ref.isOpen():
                incoming = self.serial_ref.read(in_waiting)
            else:
                self.handle_error("Serial port wasn't open for reading...", traceback.format_stack())
                return None

        except BaseException as error:
            self.handle_error(error, traceback.format_stack())
            return None

        if len(incoming) > 0:
            # append to the buffer
            try:
                self.buffer += incoming.decode("utf-8", "ignore")
            except UnicodeDecodeError as error:
                self.handle_error(error, traceback.format_stack())
                return None

            # apply a regex pattern to remove invalid characters
            buf = self.buffer_pattern.sub('', self.buffer)
            if len(self.buffer) != len(buf):
                self.debug_print("Invalid characters found:", repr(self.buffer))
            self.buffer = buf

            if len(self.buffer) > len(self.packet_end):
                # split based on user defined packet end
                packets = self.buffer.split(self.packet_end)
                self.prev_read_packets = packets

                # reset the buffer. If the buffer ends with \n, the last element in packets will be an empty string
                self.buffer = packets.pop(-1)

                return packets
        return []

    def write_packet(self, packet):
        """
        Safely write a packet over serial. Automatically appends packet_end to the input.
        This method is run on the main thread

        For initialization and process use

        :param packet: an arbitrary string without packet_end in it
        :return: True or False if the write was successful
        """

        # keep track of the previously sent packet for debugging
        self.prev_write_packet = str(packet)
        try:
            data = bytearray(str(packet) + self.packet_end, 'ascii')
        except TypeError as error:
            self.handle_error(error, traceback.format_stack())
            return False

        try:
            if self.serial_ref.isOpen():
                with self.serial_lock:
                    self.serial_ref.write(data)
            else:
                self.handle_error("Serial port wasn't open for writing...", traceback.format_stack())
                return False
        except BaseException as error:
            self.handle_error(error, traceback.format_stack())
            return False

        return True

    def print_packets(self, packets):
        """
        If debug_prints is True, print repr of all incoming packets

        :param packets: a list of received packets
        :return: None
        """
        for packet in packets:
            self.debug_print("> %s" % repr(packet))

    def flush(self):
        self.debug_print("Flushing serial")
        self.serial_ref.reset_input_buffer()
        self.serial_ref.reset_output_buffer()
        self.debug_print("Serial content:", self.in_waiting())

    # ----- external and status methods -----

    def debug_print(self, *strings):
        """
        Append a print statement to the queue. They will be printed by SerialStream 
        """
        string = "[%s] %s" % (self.whoiam, " ".join(map(str, strings)))
        with self.print_out_lock:
            self.debug_print_outs.put(string)

    def change_rate(self, new_baud_rate):
        """
        Change this port's baud rate. Only works while the port is initializing
        
        For external use
        """
        self.debug_print("Setting baud to", new_baud_rate)
        with self.baud_rate.get_lock():
            self.baud_rate.value = new_baud_rate
        self.debug_print("Set baud to", self.baud_rate.value)

    def is_running(self):
        """
        Check if the port's process is running correctly

        For external use

        :return:
            -1: exit event thrown
            0: self.configured is False
            1: process hasn't started or everything is fine
        """
        with self.start_event_lock:
            if not self.start_event.is_set():  # process hasn't started
                return 1

        if not self.configured:  # protocols didn't complete successfully
            return 0

        with self.exit_event_lock:  # process has exited
            if self.exit_event.is_set():
                return -1

        return 1

    def send_stop_events(self):
        """
        When the process exits, tell the Arduino to stop
        
        For process use

        :return: True if successful
        """

        if self.start_time > 0 and time.time() - self.start_time <= 2:  # wait for arduino to listen
            time.sleep(2)

        if not self.stop_event.is_set():
            if self.check_protocol(self.stop_packet_ask, self.stop_packet_header) is None:
                self.debug_print("Failed to send stop flag!!!")
                return False
            else:
                self.debug_print("Sent stop flag")
            self.stop_event.set()

            self.debug_print("Acquiring start lock")
            with self.start_event_lock:
                if not self.start_event.is_set():
                    self.debug_print("start_event not set! Closing serial")
                    self.close_serial()
            self.debug_print("Releasing start lock")
        else:
            self.debug_print("Stop event already set!")

        return True

    def close_serial(self):
        """
        Shutdown the serial port connection

        For external use

        :return:
        """
        self.debug_print("Acquiring serial lock")
        with self.serial_lock:
            if self.configured:
                if self.serial_ref.isOpen():
                    self.serial_ref.stop()
                    self.debug_print("Closing serial")
                else:
                    self.debug_print("Serial port was already closed!")
            else:
                self.debug_print("Port wasn't configured!!")
        self.debug_print("Releasing serial lock")

    def stop(self):
        """
        Send stop packet

        For external use
        """

        self.debug_print("Acquiring exit lock")
        if not self.exit_event.is_set():
            self.exit_event.set()
        else:
            self.debug_print("Exit event already set! Error was likely thrown")
        self.debug_print("Releasing exit lock")

    def has_exited(self):
        """
        Check if the process has exited
        
        For external use
        """
        return self.exit_event.is_set()

    def __str__(self):
        return "%s(port_address=%s)" % (self.__class__.__name__, self.address)

    def __repr__(self):
        return self.__str__()
