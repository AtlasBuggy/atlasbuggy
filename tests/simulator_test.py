import asyncio
import time

from atlasbuggy import Node, Message

"""
Vector for use in IMUMessage.
"""
class Vector(object):
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

"""
Quaternion for use in IMUMessage.
"""
class Quaternion(object):
    def __init__(self, x, y, z, w):
        self.x = x
        self.y = y
        self.z = z
        self.w = w

"""
Message for SimIMU.
"""
class IMUMessage(Message):
    def __init__(self, timestamp, n, euler, accel, gyro, mag, linaccel, quat):
        self.timestamp = timestamp
        self.euler = euler
        self.accel = accel
        self.gyro = gyro
        self.mag = mag
        self.linaccel = linaccel
        self.quat = quat
        super(IMUMessage, self).__init__(timestamp, n)

"""
Node for providing simulated IMU data for a simulated robot.
"""
class SimIMU(Node):
    def __init__(self, freq=100):
        super(SimIMU, self).__init__()

        self.rob_tag = 'rob'
        self.rob_sub = self.define_subscription(self.rob_tag)
        self.rob = None

        self.period = 1/freq

        self.prev_pose = None
        self.prev_time = None

    def take(self):
        self.rob = self.rob_sub.get_producer()

    async def loop(self):
        counter = 0
        while True:
            if self.prev_pose == None:
                self.prev_pose = self.rob.pose
                self.prev_pose = self.rob.pose.prev_time
                continue

            pose = self.rob.pose
            timestamp = self.rob.pose.prev_time
            counter += 1

            euler = self.get_euler(timestamp, pose)
            accel = self.get_accel(timestamp, pose)
            gyro = self.get_gyro(timestamp, pose)
            mag = self.get_mag(timestamp, pose)
            linaccel = self.get_linaccel(timestamp, pose)
            quat = self.get_quat(timestamp, pose)

            msg = IMUMessage(timestamp, counter, euler, accel,
                gyro, mag, linaccel, quat)
            await self.broadcast(msg)

            self.prev_pose = pose
            self.prev_time = timestamp

            await asyncio.sleep(self.period)

    def get_euler(self, timestamp, pose):
        pass

    def get_accel(self, timestamp, pose):
        pass

    def get_gyro(self, timestamp, pose):
        pass

    def get_mag(self, timestamp, pose):
        pass

    def get_linaccel(self, timestamp, pose):
        pass

    def get_quat(self, timestamp, pose):
        pass

"""
Node for providing a means of simulating robot location along with sensor data.
"""
class SimRobot(Node):
    def __init__(self):
        super(Simulator, self).__init__()

        self.pose = None

    def loop(self):
        while True:
            timestamp = time.time()
