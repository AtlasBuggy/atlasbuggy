from atlasbuggy import Robot
from atlasbuggy.logparser import LogParser
from atlasbuggy.subscriptions import *
from serial_cmdline import ReaderWriterRobot

robot = Robot(write=False)

simulator = LogParser("logs/", enabled=True,
                      update_rate=0.001, log_level=10)
reader_writer = ReaderWriterRobot()

simulator.subscribe(Subscription("reader_writer", reader_writer))

robot.run(simulator)
