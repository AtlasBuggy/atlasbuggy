from atlasbuggy.microcontrollers import SerialStream
from .imu import IMU


class ImuBot(SerialStream):
    def __init__(self):
        self.imu = IMU()
        super(ImuBot, self).__init__(self.imu)

        self.link_callback(self.imu, self.received_imu)

    def received_imu(self, timestamp, packet):
        print("%0.4f, %0.4f, %0.4f" % self.imu.euler.get_tuple())
