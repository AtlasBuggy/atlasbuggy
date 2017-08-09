from atlasbuggy import Robot, AsyncStream
from atlasbuggy.subscriptions import *
import asyncio


class Producer(AsyncStream):
    """This stream produces content"""

    def __init__(self):
        self.counter = 0  # shared resource
        super(Producer, self).__init__(log_level=20)

    async def run(self):
        while self.is_running():
            await asyncio.sleep(0.1)  # wait 0.1 seconds
            self.logger.info("I'm producing '%s'" % self.counter)  # signal that counter was posted
            await self.post(self.counter)  # post the shared resource
            self.counter += 1  # change the value


class Consumer(AsyncStream):
    """This stream consumes content"""

    def __init__(self):
        super(Consumer, self).__init__(log_level=20)

        self.producer_tag = "producer"  # a unique tag naming the subscription
        self.producer = None  # instance of the producer
        self.producer_feed = None  # the object that acts a pipe between Producer and Consumer
        self.require_subscription(self.producer_tag, Update, Producer)  # signal that this is a required subscription

    def take(self, subscriptions):
        self.producer_feed = subscriptions[self.producer_tag].get_feed()  # obtain the pipe
        self.producer = subscriptions[self.producer_tag].get_stream()  # obtain the producer

    async def run(self):
        while self.is_running():
            if not self.producer_feed.empty():  # wait for producer to post something
                counter = self.producer_feed.get()  # get posted content
                self.logger.info("I consumed '%s' from %s" % (counter, self.producer.name))  # print to terminal
            await asyncio.sleep(0.5)  # wait for 0.5 seconds

robot = Robot(write=False)

producer = Producer()
consumer = Consumer()

consumer.subscribe(Update(consumer.producer_tag, producer))

robot.run(producer, consumer)