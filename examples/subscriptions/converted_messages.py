import time
import random
import asyncio

from atlasbuggy import Node, Orchestrator, run_orchestrator


class ProducerMessage:
    def __init__(self, timestamp, x=0.0, y=0.0, z=0.0):
        self.timestamp = timestamp
        self.x = x
        self.y = y
        self.z = z


class ConsumerMessage:
    def __init__(self, timestamp, a=0.0, b=0.0):
        self.timestamp = timestamp
        self.a = a
        self.b = b


class ImmutableProducer(Node):
    def __init__(self, enabled=True):
        super(ImmutableProducer, self).__init__(enabled)

    async def loop(self):
        while True:
            producer_time = time.time()

            await self.broadcast(ProducerMessage(
                producer_time,
                random.random(), random.random(), random.random()
            ))

            await asyncio.sleep(0.5)
            self.logger.info("producer time: %s" % producer_time)


class ImmutableConsumer(Node):
    def __init__(self, enabled=True):
        super(ImmutableConsumer, self).__init__(enabled, self.make_logger(write=False))

        self.producer_sub = self.define_subscription(message_type=ConsumerMessage)
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
            self.logger.info("a: %0.4f, b: %0.4f" % (message.a, message.b))
            await asyncio.sleep(0.5)



class MyOrchestrator(Orchestrator):
    def __init__(self, event_loop):
        super(MyOrchestrator, self).__init__(event_loop, self.make_logger(write=False))

        producer = ImmutableProducer()
        consumer = ImmutableConsumer(enabled=True)

        self.add_nodes(producer, consumer)

        # self.subscribe(producer, consumer, message_converter=self.good_message_converter)
        self.subscribe(producer, consumer, message_converter=self.bad_message_converter)

    def good_message_converter(self, message: ProducerMessage):
        return ConsumerMessage(message.timestamp, message.x, message.y + message.z)

    def bad_message_converter(self, message: ProducerMessage):
        return 0.0

run_orchestrator(MyOrchestrator)
