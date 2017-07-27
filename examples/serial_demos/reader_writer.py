import re
from atlasbuggy import Robot
from atlasbuggy.serial import SerialStream, SerialObject


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

            # same as:
            # self.magic_value_1, self.magic_value_2 = tuple(map(int, packet.split("\t")))

            # also same as:
            # value_1, value_2 = packet.split("\t")
            # self.magic_value_1 = int(value_1)
            # self.magic_value_2 = int(value_2)

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
        self.link_recurring(0.5, self.timed_toggle)

    def interface_received(self, timestamp, packet):
        self.logger.info("notified that interface received: '%s' @ %0.4f" % (packet, timestamp))

    def timed_toggle(self):
        self.interface.toggle()


robot = Robot()

reader_writer = ReaderWriterRobot()

robot.run(reader_writer)
