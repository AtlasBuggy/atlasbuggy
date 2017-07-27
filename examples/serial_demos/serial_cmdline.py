import re
from atlasbuggy import Robot
from atlasbuggy.subscriptions import *
from atlasbuggy.serial import SerialStream, SerialObject
from atlasbuggy.extras.cmdline import CommandLine


class ReaderWriterInterface(SerialObject):
    def __init__(self):
        self.magic_value_1 = None
        self.magic_value_2 = None

        super(ReaderWriterInterface, self).__init__("my_reader_writer_bot")

    def receive_first(self, packet):
        match = re.match(r"(?P<magic_val_1>[0-9]*)\t(?P<magic_val_2>[0-9]*)", packet)
        if match is None:
            self.logger.warning("Failed to parse initial packet: %s" % packet)
        else:
            values = match.groupdict()
            self.magic_value_1 = int(values["magic_val_1"])
            self.magic_value_2 = int(values["magic_val_2"])

    def receive(self, timestamp, packet):
        self.logger.info("interface received: '%s' @ %0.4f" % (packet, timestamp))

    def on(self):
        self.send("on")

    def off(self):
        self.send("off")

    def toggle(self):
        self.send("toggle")


class ReaderWriterRobot(SerialStream):
    def __init__(self, enabled=True, log_level=None):
        self.interface = ReaderWriterInterface()

        super(ReaderWriterRobot, self).__init__(self.interface, enabled=enabled, log_level=log_level)

        self.link_callback(self.interface, self.interface_received)

    def interface_received(self, timestamp, packet):
        self.logger.info("notified that interface received: '%s' @ %0.4f" % (packet, timestamp))

    def receive_serial_log(self, timestamp, whoiam, packet, packet_type):
        if whoiam == self.interface.whoiam:
            self.logger.info("'%s' had received: '%s' @ %0.4f" % (whoiam, packet, timestamp))
        else:
            self.logger.warning("Unrecognized whoiam ID '%s in logs! Packet: %s" % (whoiam, packet))


class MiniCommandLine(CommandLine):
    def __init__(self, enabled=True, log_level=None):

        self.reader_writer = None
        self.reader_writer_tag = "reader_writer"
        self.require_subscription(self.reader_writer_tag, Subscription, ReaderWriterRobot)

        super(MiniCommandLine, self).__init__(enabled, log_level)

    def handle_input(self, line):
        if line == "0" or line == "off":
            self.reader_writer.interface.off()
        elif line == "1" or line == "on":
            self.reader_writer.interface.on()
        if line == "2" or line == "toggle":
            self.reader_writer.interface.toggle()


robot = Robot()

reader_writer = ReaderWriterRobot()
cmdline = MiniCommandLine()

cmdline.subscribe(Subscription(cmdline.reader_writer_tag, reader_writer))

robot.run(reader_writer, cmdline)
