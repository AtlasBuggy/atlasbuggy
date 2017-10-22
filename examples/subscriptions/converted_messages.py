import os
import time
import random
import asyncio

from atlasbuggy import Node, Orchestrator, Message, run


class ProducerMessage(Message):
    def __init__(self, timestamp, n, x=0.0, y=0.0, z=0.0):
        self.timestamp = timestamp
        self.x = x
        self.y = y
        self.z = z
        super(ProducerMessage, self).__init__(timestamp, n)

    def __str__(self):
        return "ProducerMessage(t=%s, n=%s, x=%s, y=%s, z=%s)" % (self.timestamp, self.n, self.x, self.y, self.z)


class ConsumerMessage(Message):
    def __init__(self, timestamp, n, a=0.0, b=0.0):
        self.timestamp = timestamp
        self.a = a
        self.b = b
        super(ConsumerMessage, self).__init__(timestamp, n)

    def __str__(self):
        return "ConsumerMessage(t=%s, n=%s a=%s, b=%s)" % (self.timestamp, self.n, self.a, self.b)


class ImmutableProducer(Node):
    def __init__(self, enabled=True):
        super(ImmutableProducer, self).__init__(enabled)

    async def loop(self):
        counter = 0
        while True:
            producer_time = time.time()
            message = ProducerMessage(
                producer_time, counter,
                random.random(), random.random(), random.random()
            )
            counter += 1
            await self.broadcast(message)

            await asyncio.sleep(0.5)
            self.logger.info("sending: %s" % message)


class ImmutableConsumer(Node):
    def __init__(self, enabled=True):
        super(ImmutableConsumer, self).__init__(enabled)

        self.producer_tag = "producer"
        self.producer_sub = self.define_subscription(self.producer_tag, message_type=ConsumerMessage)
        self.producer_queue = None
        self.producer = None

    def take(self):
        self.producer_queue = self.producer_sub.get_queue()
        self.producer = self.producer_sub.get_producer()

        self.logger.info("Got producer named '%s'" % self.producer.name)

    async def loop(self):
        while True:
            message = await self.producer_queue.get()
            consumer_time = time.time()

            self.logger.info("time diff: %s" % (consumer_time - message.timestamp))
            self.logger.info("receiving: %s" % message)
            await asyncio.sleep(0.5)


class MyOrchestrator(Orchestrator):
    def __init__(self, event_loop):
        self.set_default(write=True, file_name="converted_messages_demo.log",
                         directory=os.path.join("logs", "converted_messages_demo", "%(name)s"))

        super(MyOrchestrator, self).__init__(event_loop)

        producer = ImmutableProducer()
        consumer = ImmutableConsumer(enabled=True)

        self.add_nodes(producer, consumer)

        self.subscribe(producer, consumer, consumer.producer_tag, message_converter=self.good_message_converter)
        # self.subscribe(producer, consumer, consumer.producer_tag, message_converter=self.bad_message_converter)

    def good_message_converter(self, message: ProducerMessage):
        return ConsumerMessage(message.timestamp, message.n, message.x, message.y + message.z)

    def bad_message_converter(self, message: ProducerMessage):
        return 0.0


if __name__ == '__main__':
    run(MyOrchestrator)
