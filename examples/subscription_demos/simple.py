from atlasbuggy import Robot, DataStream, AsyncStream
from atlasbuggy.subscriptions import *
import asyncio


class SomeStream(AsyncStream):
    """This stream runs and performs some tasks on a stream is subscribes to"""

    def __init__(self):
        super(SomeStream, self).__init__(log_level=20)

        self.static_stream_tag = "static"  # a unique tag naming the subscription
        self.static_stream = None  # instance of the stream being subscribed to

        # signal that this is a required subscription. The producer stream must have attributes
        # "get_counter", "set_counter", and "set_timer"
        self.require_subscription(self.static_stream_tag, Subscription, StaticStream,
                                  required_attributes=("get_counter", "set_counter", "set_timer"))

    def take(self, subscriptions):
        self.static_stream = subscriptions[self.static_stream_tag].get_stream()  # obtain the producer

    async def run(self):
        while self.is_running():
            await asyncio.sleep(0.5)  # wait for 0.5 seconds

            # update the producer stream's counter
            counter = self.static_stream.get_counter()
            counter += 1
            self.static_stream.set_counter(counter)
            self.logger.info("Setting %s's counter to %s" % (self.static_stream.name, counter))

            # update the producer stream's time
            current_time = self.dt()
            self.static_stream.set_timer(current_time)
            self.logger.info("Setting %s's time to %0.4f" % (self.static_stream.name, current_time))

    def stop(self):
        self.logger.info("Good bye!")


class StaticStream(DataStream):
    def __init__(self):
        super(StaticStream, self).__init__(log_level=20)

        # shared resources
        self.counter = 0
        self.timer = 0.0

    def start(self):
        """Static streams don't have their run methods called"""
        self.logger.info("Hello! I'm a static stream")

    def stopped(self):
        """Static streams don't have their run methods called. stop will not be called, stopped will be"""
        self.logger.info("Good bye!")

    def get_counter(self):
        """
        A required method as a producer for 'SomeStream'
        Returns the counter's current value
        """
        return self.counter

    def set_counter(self, new_count):
        """
        A required method as a producer for 'SomeStream'
        Sets the counter's value
        """
        self.counter = new_count
        self.logger.info("Someone just set my counter to %s" % self.counter)

    def set_timer(self, new_time):
        """
        A required method as a producer for 'SomeStream'
        Sets the timer's value
        """
        self.timer = new_time
        self.logger.info("Someone just set my time to %0.4f. My current time is %0.4f" % (self.timer, self.dt()))


robot = Robot(write=False, log_level=10)

static = StaticStream()
some_stream = SomeStream()

some_stream.subscribe(Subscription(some_stream.static_stream_tag, static))

robot.run(static, some_stream)
