import time
import random
import asyncio
from atlasbuggy import Orchestrator, Node, run

DEMONSTRATE_ERROR = True


class SomeMessage1:
    def __init__(self, timestamp, x, y, z):
        self.timestamp = timestamp
        self.x = x
        self.y = y
        self.z = z


class SomeMessage2:
    def __init__(self, timestamp, a):
        self.timestamp = timestamp
        self.a = a

class SomeMessage3:
    def __init__(self, timestamp, a, b):
        self.timestamp = timestamp
        self.a = a
        self.b = b


class ProducerNode(Node):
    def __init__(self, enabled=True):
        super(ProducerNode, self).__init__(enabled)

    async def loop(self):
        counter = 0
        while True:
            producer_time = time.time()

            if counter % 2 == 0:
                await self.broadcast(SomeMessage1(
                    producer_time,
                    random.random(), random.random(), random.random()
                ))
            elif DEMONSTRATE_ERROR and counter % 3 == 0:
                await self.broadcast(SomeMessage3(
                    producer_time,
                    counter, random.random()
                ))
            else:
                await self.broadcast(SomeMessage2(
                    producer_time,
                    counter
                ))
            counter += 1


            await asyncio.sleep(0.5)
            self.logger.info("producer time: %s" % producer_time)


class ConsumerNode(Node):
    def __init__(self, enabled=True):
        super(ConsumerNode, self).__init__(enabled, self.make_logger(write=False))

        self.producer_tag = "producer"
        self.producer_sub = self.define_subscription(self.producer_tag, message_type=(SomeMessage1, SomeMessage2))
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

            if type(message) == SomeMessage1:
                self.logger.info("x: %0.4f, y: %0.4f, z: %0.4f" % (message.x, message.y, message.z))
            else:
                self.logger.info("a: %s" % message.a)
            await asyncio.sleep(0.5)


class MyOrchestrator(Orchestrator):
    def __init__(self, event_loop):
        super(MyOrchestrator, self).__init__(event_loop, self.make_logger(write=False))

        producer = ProducerNode()
        consumer = ConsumerNode()

        self.add_nodes(producer, consumer)
        self.subscribe(consumer.producer_tag, producer, consumer)


run(MyOrchestrator)
