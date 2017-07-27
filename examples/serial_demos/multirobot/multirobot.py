from atlasbuggy.serial import SerialStream
from robot1 import Robot1
from robot2 import Robot2
from robot3 import Robot3


class MultiRobotManager(SerialStream):
    def __init__(self, enabled=True, log_level=None):
        self.robot_1 = Robot1()
        self.robot_2 = Robot2()
        self.robot_3 = Robot3()

        super(MultiRobotManager, self).__init__(self.robot_1, self.robot_2, self.robot_3,
                                                enabled=enabled, log_level=log_level)

        self.link_callback(self.robot_1, self.bot1_received)
        self.link_callback(self.robot_2, self.bot2_received)
        self.link_callback(self.robot_3, self.bot3_received)

    def serial_start(self):
        # note how I'm not calling start. Start is already used by SerialStream and should not be overridden
        self.robot_1.on()

    def bot1_received(self, timestamp, packet):
        if self.robot_1.led_state and self.robot_1.current_arduino_msec % 1000 == 0:
            self.robot_2.on()
            self.robot_1.off()

    def bot2_received(self, timestamp, packet):
        if self.robot_2.led_state and self.robot_2.current_arduino_msec % 1000 == 0:
            self.robot_3.on()
            self.robot_2.off()

    def bot3_received(self, timestamp, packet):
        if self.robot_3.led_state and self.robot_3.current_arduino_msec % 1000 == 0:
            self.robot_1.on()
            self.robot_3.off()

    def receive_serial_log(self, timestamp, whoiam, packet, packet_type):
        if whoiam == self.robot_1.whoiam:
            self.logger.info("'%s' had received: '%s' @ %0.4f" % (whoiam, packet, timestamp))
        else:
            self.logger.warning("Unrecognized whoiam ID '%s in logs! Packet: %s" % (whoiam, packet))
