import re
import asyncio
import threading
import time
import traceback

import serial.tools.list_ports

from atlasbuggy.datastream import AsyncStream
from atlasbuggy.serial.clock import Clock, CommandPause, RecurringEvent
from atlasbuggy.serial.errors import *
from atlasbuggy.serial.object import SerialObject
from atlasbuggy.serial.port import SerialPort


class SerialStream(AsyncStream):
    def __init__(self, *serial_objects, enabled=True, log_level=None, name=None):
        super(SerialStream, self).__init__(enabled, name, log_level)

        self.objects = {}
        self.ports = {}
        self.callbacks = {}
        self.recurring = []

        self.packet = ""

        self.loops_per_second = 200
        self.loop_delay = 1 / self.loops_per_second
        self.clock = Clock(self.loops_per_second)
        self.object_list = serial_objects

        self.init_objects(self.object_list)

        self.port_pattern = re.compile(
            r"<(?P<timestamp>[.0-9a-zA-Z]*), (?P<whoiam>.*), \[(?P<portname>.*)\] (?P<message>.*), debug>"
        )
        self.packet_pattern = re.compile(
            r"<(?P<timestamp>[.0-9a-zA-Z]*), (?P<whoiam>.*), (?P<message>.*), (?P<packettype>.*)>"
        )

    def time_started(self):
        return None

    def link_callback(self, arg, callback_fn):
        """
        :param arg:
        :param callback_fn: function that takes the parameters timestamp and packet
        :return:
        """
        if type(arg) == str and arg in self.objects.keys():
            whoiam = arg
        elif isinstance(arg, SerialObject):
            whoiam = arg.whoiam
        else:
            raise RobotObjectInitializationError("Linked callback input is an invalid whoiam ID or invalid object:",
                                                 repr(arg))
        self.callbacks[whoiam] = callback_fn

    def link_recurring(self, repeat_time, callback_fn, *args, include_event_in_params=False):
        self.recurring.append(RecurringEvent(repeat_time, time.time(), callback_fn, args, include_event_in_params))

    def init_objects(self, serial_objects):
        for serial_object in serial_objects:
            serial_object.is_live = True
            if isinstance(serial_object, SerialObject):
                self.objects[serial_object.whoiam] = serial_object
            else:
                raise RobotObjectInitializationError(
                    "Object passed is not valid:", repr(serial_object))

    def init_ports(self):
        discovered_ports = []
        for port_address in self.list_ports():
            discovered_ports.append(SerialPort(port_address))
        self.logger.debug("Discovered ports: " + str(discovered_ports))

        threads = []
        error_messages = []
        for serial_port in discovered_ports:
            config_thread = threading.Thread(target=self.configure_port, args=(serial_port, error_messages))
            threads.append(config_thread)
            config_thread.start()

        for thread in threads:
            thread.join()

        for error_id, message in error_messages:
            if error_id == 0:
                raise RobotSerialPortWhoiamIdTaken(message)
            elif error_id == 1:
                raise RobotSerialPortNotConfiguredError(message)

        if self.ports.keys() != self.objects.keys():
            unassigned_ids = self.objects.keys() - self.ports.keys()
            if len(unassigned_ids) == 1:
                message = "Failed to assign object with ID "
            else:
                message = "Failed to assign objects with IDs "
            raise RobotObjectNotFoundError(message + str(list(unassigned_ids))[1:-1])

        self.validate_ports()

        for whoiam in self.ports.keys():
            self.logger.debug("[%s] has ID '%s'" % (self.ports[whoiam].address, whoiam))

    def dt(self, current_time=None, use_current_time=False):
        if use_current_time:
            if current_time is None:
                self.timestamp = time.time()
            else:
                self.timestamp = current_time

        if self.start_time is None or self.timestamp is None:
            return 0.0
        else:
            return self.timestamp - self.start_time

    def configure_port(self, serial_port, errors_list):
        """
        Initialize a serial port recognized by pyserial.
        Only devices that are plugged in should be recognized
        """
        # initialize SerialPort
        serial_port.initialize()

        # check for duplicate IDs
        if serial_port.whoiam in self.ports.keys():
            errors_list.append((0, "whoiam ID already being used by another port! It's possible "
                                   "the same code was uploaded for two boards.\n"
                                   "Port address: %s, ID: %s" % (serial_port.address, serial_port.whoiam)))

        # check if port abides protocol. Warn the user and stop the port if not (ignore it essentially)
        elif serial_port.configured and (not serial_port.abides_protocols or serial_port.whoiam is None):
            self.logger.debug("Warning! Port '%s' does not abide by protocol!" % serial_port.address)
            serial_port.stop()

        # check if port is configured correctly
        elif not serial_port.configured:
            errors_list.append((1, "Port not configured! '%s'" % serial_port.address))

        # disable ports if the corresponding object if disabled
        elif not self.objects[serial_port.whoiam].enabled:
            serial_port.stop()
            self.logger.debug("Ignoring port with ID: %s (Disabled by user)" % serial_port.whoiam)

        # add the port if configured and abides protocol
        else:
            self.ports[serial_port.whoiam] = serial_port

    def validate_ports(self):
        """
        Validate that all ports are assigned to enabled objects. Warn the user otherwise
            (this allows for ports not listed in objects to be plugged in but not used)
        """
        used_ports = {}
        for whoiam in self.ports.keys():
            if whoiam not in self.objects.keys():
                self.logger.warning("Port ['%s', %s] is unused!" % (self.ports[whoiam].address, whoiam))
            else:
                # only append port if its used. Ignore it otherwise
                used_ports[whoiam] = self.ports[whoiam]

                # if a robot object signals it wants a different baud rate, change to that rate
                object_baud = self.objects[whoiam].baud
                if object_baud is not None and object_baud != self.ports[whoiam].baud_rate:
                    self.ports[whoiam].change_rate(object_baud)
        self.ports = used_ports

    def list_ports(self):
        port_addresses = []

        # return the port if 'USB' is in the description
        for port_no, description, address in serial.tools.list_ports.comports():
            if 'USB' in address:
                port_addresses.append(port_no)
        return port_addresses

    def first_packets(self):
        """
        Send each port's first packet to the corresponding object if it isn't an empty string
        """
        for whoiam in self.objects.keys():
            first_packet = self.ports[whoiam].first_packet
            if len(first_packet) > 0:
                self.deliver_first_packet(whoiam, first_packet)

                # record first packets
                self.record(None, whoiam, first_packet, "object")
        self.logger.debug("First packets sent")

    def deliver_first_packet(self, whoiam, first_packet):
        error = None
        try:
            if self.objects[whoiam].receive_first(first_packet) is not None:
                self.logger.warning("Closing all from first_packets()")
                self.stop()
                self.exit()
        except BaseException as _error:
            self.stop()
            self.exit()
            error = _error

        if error is not None:
            raise self.handle_error(
                RobotObjectReceiveError(whoiam, first_packet),
                traceback.format_stack()
            ) from error

        self.received(whoiam)

    def start(self):
        self.start_time = time.time()
        self.clock.start(self.start_time)
        self.init_ports()

        self.first_packets()

        for robot_port in self.ports.values():
            if not robot_port.send_start():
                self.stop()
                raise self.handle_error(
                    RobotSerialPortWritePacketError(
                        "Unable to send start packet!", self.timestamp, self.packet, robot_port),
                    traceback.format_stack()
                )

        # start port processes
        for robot_port in self.ports.values():
            robot_port.start()

        self.logger.debug("SerialStream is starting")
        error = None
        try:
            self.serial_start()
        except BaseException as _error:
            self.stop()
            self.exit()
            error = _error

        if error is not None:
            raise error

    def serial_start(self):
        pass

    async def run(self):
        self.logger.debug("SerialStream is running")
        while self.running():
            for port in self.ports.values():
                self.check_port_packets(port)

            self.update_recurring(time.time())
            self.send_commands()

            # if no packets have been received for a while, update the timestamp with the current clock time
            # current_real_time = time.time() - self.start_time
            # if self.timestamp is None or current_real_time - self.timestamp > 0.01 or len(self.ports) == 0:
            #     self.timestamp = current_real_time

            await asyncio.sleep(self.loop_delay)
            # self.clock.update()  # maintain a constant loop speed

    def update_recurring(self, timestamp):
        for event in self.recurring:
            event.update(timestamp)

    def check_port_packets(self, port):
        with port.lock:
            self.check_port_status(port)

            while not port.packet_queue.empty():
                self.timestamp, self.packet = port.packet_queue.get()
                port.counter.value -= 1

                self.deliver(port.whoiam)
                self.received(port.whoiam)

                self.record(self.timestamp, port.whoiam, self.packet, "object")
                self.record_debug_prints(self.timestamp, port)

                port.queue_len = port.counter.value

    def check_port_status(self, port):
        """
        Check if the process is running properly. An error will be thrown if not.

        :return: True if the ports are ok
        """

        status = port.is_running()
        if status < 1:
            self.logger.warning("Closing all from check_port_status")
            self.stop()
            self.logger.debug("status:", status)
            if status == 0:
                raise self.handle_error(
                    RobotSerialPortNotConfiguredError(
                        "Port with ID '%s' isn't configured!" % port.whoiam, self.timestamp, self.packet,
                        port),
                    traceback.format_stack()
                )
            elif status == -1:
                raise self.handle_error(
                    RobotSerialPortSignalledExitError(
                        "Port with ID '%s' signalled to exit" % port.whoiam, self.timestamp, self.packet,
                        port),
                    traceback.format_stack()
                )

    def received(self, whoiam):
        error = None
        try:
            if whoiam in self.callbacks:
                if self.callbacks[whoiam](self.timestamp, self.packet) is not None:
                    self.logger.warning(
                        "callback with whoiam ID: '%s' signalled to exit. Packet: %s" % (
                            whoiam, repr(self.packet)))
                    self.stop()
        except BaseException as _error:
            self.logger.warning("Closing all from received")
            self.stop()
            self.exit()
            error = _error

        if error is not None:
            raise self.handle_error(
                PacketReceivedError(error),
                traceback.format_stack()
            ) from error

    def deliver(self, whoiam):
        error = None
        try:
            if self.objects[whoiam].receive(self.timestamp, self.packet) is not None:
                self.logger.warning(
                    "receive for object signalled to exit. whoiam ID: '%s', packet: %s" % (
                        whoiam, repr(self.packet)))
                self.stop()
        except BaseException as _error:
            self.logger.warning("Closing from deliver")
            self.stop()
            self.exit()
            error = _error

        if error is not None:
            raise self.handle_error(
                RobotObjectReceiveError(whoiam, self.packet),
                traceback.format_stack()
            ) from error

    def send_commands(self):
        """
        Check every robot object. Send all commands if there are any
        """
        for whoiam in self.objects.keys():
            # loop through all commands and send them
            while not self.objects[whoiam].command_packets.empty():
                if self.objects[whoiam]._pause_command is not None:
                    if self.objects[whoiam]._pause_command.update():
                        self.objects[whoiam]._pause_command = None
                    else:
                        break

                command = self.objects[whoiam].command_packets.get()

                if isinstance(command, CommandPause):
                    self.objects[whoiam]._pause_command = command
                    self.objects[whoiam]._pause_command.prev_time = time.time()
                    self.record(time.time(), whoiam, str(command.delay_time), "pause command")
                else:
                    # log sent command.
                    self.record(time.time(), whoiam, command, "command")

                    # if write packet fails, throw an error
                    if not self.ports[whoiam].write_packet(command):
                        self.logger.warning("Closing all from _send_commands")
                        self.stop()
                        self.exit()
                        raise self.handle_error(
                            RobotSerialPortWritePacketError(
                                "Failed to send command %s to '%s'" % (command, whoiam), self.timestamp, self.packet,
                                self.ports[whoiam]),
                            traceback.format_stack())

    def record(self, timestamp, whoiam, packet, packet_type):
        """
        object        : from a robot object
        user          : user logged
        command       : command sent
        pause command : pause command
        debug         : port debug message
        """
        self.logger.debug("<%s, %s, %s, %s>" % (timestamp, whoiam, packet, packet_type))

    def handle_error(self, error, traceback):
        error_message = "".join(traceback[:-1])
        error_message += "%s: %s" % (error.__class__.__name__, error.args[0])
        error_message += "\n".join(error.args[1:])
        self.logger.error(error_message)

        self.grab_all_port_prints()
        return error

    def grab_all_port_prints(self):
        for port in self.ports.values():
            self.record_debug_prints(self.timestamp, port)
        self.logger.debug("Port debug prints recorded")

    def record_debug_prints(self, timestamp, port):
        """
        Take all of the port's queued debug messages and record them
        :param timestamp: current timestamp
        :param port: RobotSerialPort
        """
        with port.print_out_lock:
            while not port.debug_print_outs.empty():
                self.record(timestamp, port.whoiam, port.debug_print_outs.get(), "debug")

    def stop_all_ports(self):
        """
        Close all robot port processes
        """
        self.logger.debug("Closing all ports")

        # stop port processes
        for robot_port in self.ports.values():
            self.logger.debug("closing '%s'" % robot_port.whoiam)
            robot_port.stop()

        for robot_port in self.ports.values():
            self.logger.debug("[%s] Port previous packets: read: %s, write %s" % (
                robot_port.whoiam,
                repr(robot_port.prev_read_packets), repr(robot_port.prev_write_packet)))
        time.sleep(0.01)
        # check if the port exited properly
        for port in self.ports.values():
            has_exited = port.has_exited()
            self.logger.debug("%s, '%s' has %s" % (port.address, port.whoiam,
                                                   "exited" if has_exited else "not exited!!"))
            if not has_exited:
                raise self.handle_error(RobotSerialPortFailedToStopError(
                    "Port signalled error while stopping", self.timestamp, self.packet,
                    port), traceback.format_stack())
        self.logger.debug("All ports exited")

    def stop(self):
        """
        Close all SerialPort processes and close their serial ports
        """
        error = None
        try:
            self.serial_close()
        except BaseException as error:
            self.handle_error(error, traceback.format_stack())

        self.send_commands()
        self.logger.debug("Sent last commands")
        self.stop_all_ports()
        self.logger.debug("Closed ports successfully")
        self.grab_all_port_prints()

        if error is not None:
            self.exit()
            raise error

    def serial_close(self):
        pass

    def receive_log(self, message, line_info):
        if not self.match_port_debug(message):
            self.match_log(message, line_info)

    def match_port_debug(self, message):
        matches = re.finditer(self.port_pattern, message)
        matched = False
        for match_num, match in enumerate(matches):
            matched = True
            matchdict = match.groupdict()
            self.logger.debug("[%(timestamp)s, %(whoiam)s, %(portname)s]: %(message)s" % matchdict)
        return matched

    def match_log(self, packet, line_info):
        matches = re.finditer(self.packet_pattern, packet)

        for match_num, match in enumerate(matches):
            matchdict = match.groupdict()
            timestamp = matchdict["timestamp"]
            whoiam = matchdict["whoiam"]
            packet = matchdict["message"]
            packet_type = matchdict["packettype"]

            if timestamp == "None":
                self.timestamp = None
            else:
                self.timestamp = float(timestamp)
                if self.start_time is None:
                    self.start_time = self.timestamp

            if packet_type == "object":
                if self.timestamp is None:
                    self.deliver_first_packet(whoiam, packet)
                else:
                    self.packet = packet

                    self.deliver(whoiam)
                    self.received(whoiam)

            self.received_log(self.timestamp, whoiam, packet, packet_type)

    def received_log(self, timestamp, whoiam, packet, packet_type):
        pass
