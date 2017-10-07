from atlasbuggy import Robot, AsyncStream
from atlasbuggy.subscriptions import *
import asyncio


class IntMessage:
    def __init__(self):
        self.num1 = 0
        self.num2 = 0

    def __str__(self):
        return "%s(num1=%s, num2=%s)" % (IntMessage.__name__, self.num1, self.num2)


class Producer(AsyncStream):
    """This stream produces content"""

    def __init__(self):
        self.message = IntMessage()  # shared resource
        super(Producer, self).__init__(log_level=20)

        self.adjust_service("default", message_class=IntMessage)

    async def run(self):
        while self.is_running():
            await asyncio.sleep(0.5)  # wait 0.5 seconds
            self.message.num1 += 1  # change the value
            self.message.num2 += 1

            self.logger.info("I'm producing '%s'" % str(self.message))  # signal that counter was posted
            await self.post(self.message)  # post the shared resource

    def stop(self):
        self.logger.info("Good bye!")


class Consumer(AsyncStream):
    """This stream consumes content"""

    def __init__(self):
        super(Consumer, self).__init__(log_level=20)

        self.producer_tag = "producer"  # a unique tag naming the subscription
        self.producer_feed = None  # the object that acts a queue between Producer and Consumer
        self.require_subscription(self.producer_tag, Feed, Producer,
                                  required_message_classes=None)  # signal that this is a required subscription

    def take(self, subscriptions):
        self.producer_feed = subscriptions[self.producer_tag].get_feed()  # obtain the queue

    async def run(self):
        # while self.is_running():
        #     counter = await self.producer_feed.get()  # wait for producer to post something
        #     self.producer_feed.task_done()  # when you're done getting, make sure to call this
        #     self.logger.info("I consumed '%s'" % counter)  # print to terminal

        while self.is_running():
            await self.get_counter()
            while not self.producer_feed.empty():
                await self.get_counter()
            self.producer_feed.task_done()  # when you're done getting, make sure to call this

    async def get_counter(self):
        message = await self.producer_feed.get()  # wait for producer to post something
        self.logger.info("I consumed '%s'" % str(message))  # print to terminal

    def stop(self):
        self.logger.info("Good bye!")


robot = Robot(write=False)

producer = Producer()
consumer = Consumer()

consumer.subscribe(Feed(consumer.producer_tag, producer))

robot.run(producer, consumer)
