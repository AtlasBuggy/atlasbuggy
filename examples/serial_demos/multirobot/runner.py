from atlasbuggy import Robot
from multirobot import MultiRobotManager

robot = Robot(log_level=10)
multibot = MultiRobotManager()
robot.run(multibot)
