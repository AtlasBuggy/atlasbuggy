from atlasbuggy import Robot
from atlasbuggy.logparser import LogParser
from atlasbuggy.subscriptions import *
from imu_bot import ImuBot

robot = Robot(write=False)

simulator = LogParser("logs/test.log.xz", enabled=True,
                      update_rate=0.001, log_level=10)
imu_bot = ImuBot()

simulator.subscribe(Subscription(imu_bot.name, imu_bot))

robot.run(simulator)
