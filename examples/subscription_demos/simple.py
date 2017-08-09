from atlasbuggy import Robot, DataStream, AsyncStream
from atlasbuggy.subscriptions import *
import asyncio


class SomeStream(AsyncStream):
    """This stream runs and performs some tasks on a stream is subscribes to"""

    def __init__(self):
        super(SomeStream, self).__init__(log_level=20)  # logger.info statements will show up in the output

        self.static_stream_tag = "static"  # a unique tag naming the subscription
        self.static_stream = None  # instance of the stream being subscribed to

        # signal that this is a required subscription. The producer stream must have attributes
        # "counter", "increment_counter", and "set_timer"
        self.require_subscription(self.static_stream_tag, Subscription, StaticStream,
                                  required_methods=("increment_counter", "set_timer"),
                                  required_attributes=("counter",))

    def take(self, subscriptions):
        self.static_stream = subscriptions[self.static_stream_tag].get_stream()  # obtain the producer

    async def run(self):
        while self.is_running():
            await asyncio.sleep(0.5)  # wait for 0.5 seconds

            # update the producer stream's counter
            self.static_stream.increment_counter()
            self.logger.info("Setting %s's counter to %s" % (self.static_stream.name, self.static_stream.counter))

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

    def increment_counter(self):
        """
        A required method as a producer for 'SomeStream'
        Increments the counter's value
        """
        self.counter += 1
        self.logger.info("Someone just set my counter to %s" % self.counter)

    def set_timer(self, new_time):
        """
        A required method as a producer for 'SomeStream'
        Sets the timer's value
        """
        self.timer = new_time
        dt = self.dt()
        self.logger.info("Someone just set my time to %0.4f. My current time is %0.4f\n"
                         "The difference is %s" % (self.timer, dt, dt - new_time))


robot = Robot(write=False)

static = StaticStream()
some_stream = SomeStream()

some_stream.subscribe(Subscription(some_stream.static_stream_tag, static))

robot.run(static, some_stream)
