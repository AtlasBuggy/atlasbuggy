import time
import random
import asyncio
from atlasbuggy import Orchestrator, Node, run_orchestrator

DEMONSTRATE_ERROR = False


class SomeMessage:
    def __init__(self, timestamp, x=0.0, y=0.0, z=0.0):
        self.timestamp = timestamp
        self.x = x
        self.y = y
        self.z = z


class ProducerNode(Node):
    def __init__(self, enabled=True):
        super(ProducerNode, self).__init__(enabled)

    async def loop(self):
        while True:
            producer_time = time.time()

            if DEMONSTRATE_ERROR:
                await self.broadcast(producer_time)
            else:
                await self.broadcast(SomeMessage(
                    producer_time,
                    random.random(), random.random(), random.random()
                ))

            await asyncio.sleep(0.5)
            self.logger.info("producer time: %s" % producer_time)


class ConsumerNode(Node):
    def __init__(self, enabled=True):
        super(ConsumerNode, self).__init__(enabled, self.make_logger(write=False))

        self.producer_sub = self.define_subscription(message_type=SomeMessage)
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
            self.logger.info("x: %0.4f, y: %0.4f, z: %0.4f" % (message.x, message.y, message.z))
            await asyncio.sleep(0.5)


class MyOrchestrator(Orchestrator):
    def __init__(self, event_loop):
        super(MyOrchestrator, self).__init__(event_loop, self.make_logger(write=False))

        producer = ProducerNode()
        consumer = ConsumerNode()

        self.add_nodes(producer, consumer)

        self.subscribe(producer, consumer)


run_orchestrator(MyOrchestrator)
