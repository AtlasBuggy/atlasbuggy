import time
from atlasbuggy import Robot, AsyncStream, ThreadedStream
from atlasbuggy.subscriptions import *
import asyncio


class Producer(AsyncStream):
    """This stream produces content asynchronously"""

    def __init__(self):
        self.counter = 0  # shared resource
        super(Producer, self).__init__(log_level=20)

    async def run(self):
        while self.is_running():
            await asyncio.sleep(0.1)  # wait 0.1 seconds
            self.logger.info("I'm producing '%s'" % self.counter)  # signal that counter was posted
            await self.post(self.counter)  # post the shared resource
            self.counter += 1  # change the value

    def stop(self):
        self.logger.info("Good bye!")


class Consumer(ThreadedStream):
    """This stream consumes content on a thread"""

    def __init__(self):
        super(Consumer, self).__init__(log_level=20)

        self.producer_tag = "producer"  # a unique tag naming the subscription
        self.producer_feed = None  # the object that acts a pipe between Producer and Consumer
        self.require_subscription(self.producer_tag, Feed, Producer)  # signal that this is a required subscription

    def take(self, subscriptions):
        self.producer_feed = subscriptions[self.producer_tag].get_feed()  # obtain the pipe

    def run(self):
        while self.is_running():
            while not self.producer_feed.empty():
                counter = self.producer_feed.get()  # wait for producer to post something
                self.producer_feed.task_done()  # when you're done getting, make sure to call this
                self.logger.info("I consumed '%s'" % counter)  # print to terminal
            time.sleep(0.5)  # wait for 0.5 seconds
            raise Exception("something")

    def stop(self):
        self.logger.info("Good bye!")


robot = Robot(write=False)

producer = Producer()
consumer = Consumer()

consumer.subscribe(Feed(consumer.producer_tag, producer))

robot.run(producer, consumer)
