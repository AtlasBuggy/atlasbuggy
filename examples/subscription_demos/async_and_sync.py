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

        # self.set_to_daemon()

    def take(self, subscriptions):
        self.producer_feed = subscriptions[self.producer_tag].get_feed()  # obtain the pipe

    def run(self):
        # while self.is_running():
        #     self.get_counter()
        #     while not self.producer_feed.empty():
        #         self.get_counter()
        #     self.producer_feed.task_done()

        # while self.is_running():
        #     while not self.producer_feed.empty():
        #         if not self.is_running():  # prevent the loop from processing frame after shutdown
        #             return
        #
        #         self.get_counter()
        #
        #         time.sleep(0.5)  # some time consuming operation
        #
        #         self.producer_feed.task_done()
        #     time.sleep(0.05)

        while self.is_running():
            while not self.producer_feed.empty():
                self.get_counter()
                self.producer_feed.task_done()
            time.sleep(0.05)

    def get_counter(self):
        counter = self.producer_feed.get()  # wait for producer to post something
        self.logger.info("I consumed '%s'" % counter)  # print to terminal

    def stop(self):
        self.logger.info("Good bye!")


robot = Robot(write=False, log_level=10)

producer = Producer()
consumer = Consumer()

consumer.subscribe(Feed(consumer.producer_tag, producer))

robot.run(producer, consumer)
