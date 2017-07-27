
from atlasbuggy import Robot
from atlasbuggy.logparser import LogParser
from atlasbuggy.subscriptions import *
from .serial_cmdline import ReaderWriterRobot

robot = Robot()

simulator = LogParser("fill with the path to your log file", enabled=True, update_rate=0.001)
reader_writer = ReaderWriterRobot()

simulator.subscribe(Subscription("reader_writer", reader_writer))

robot.run(simulator)