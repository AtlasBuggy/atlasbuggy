import re
from atlasbuggy.serial import SerialObject


class BaseRobot(SerialObject):
    def __init__(self, whoiam, enabled):
        self.current_arduino_msec = None
        self.led_state = None

        super(BaseRobot, self).__init__(whoiam, enabled)

    def receive(self, timestamp, packet):
        match = re.match(r"(?P<time>[0-9]*)\t(?P<led_state>[0-9]*)", packet)
        if match is None:
            self.logger.warning("Failed to parse initial packet: %s" % packet)
        else:
            values = match.groupdict()
            self.current_arduino_msec = int(values["time"])
            self.led_state = bool(int(values["led_state"]))

    def on(self):
        self.send("on")

    def off(self):
        self.send("off")

    def toggle(self):
        self.send("toggle")
