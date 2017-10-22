import time
import random
import asyncio
from atlasbuggy import Orchestrator, Node, Message, run

DEMONSTRATE_ERROR = False


class SomeMessage(Message):
    def __init__(self, timestamp, n, x=0.0, y=0.0, z=0.0):
        self.timestamp = timestamp
        self.x = x
        self.y = y
        self.z = z

        super(SomeMessage, self).__init__(timestamp, n)


class ProducerNode(Node):
    def __init__(self, enabled=True):
        super(ProducerNode, self).__init__(enabled)

    async def loop(self):
        counter = 0
        while True:
            producer_time = time.time()

            if DEMONSTRATE_ERROR:
                await self.broadcast(producer_time)
            else:
                await self.broadcast(SomeMessage(
                    producer_time, counter,
                    random.random(), random.random(), random.random()
                ))
                counter += 1

            await asyncio.sleep(0.5)
            self.logger.info("producer time: %s" % producer_time)


class ConsumerNode(Node):
    def __init__(self, enabled=True):
        self.set_logger(write=False)
        super(ConsumerNode, self).__init__(enabled)

        self.producer_tag = "producer"
        self.producer_sub = self.define_subscription(self.producer_tag, message_type=SomeMessage)
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
            self.logger.info("n: %s, x: %0.4f, y: %0.4f, z: %0.4f" % (message.n, message.x, message.y, message.z))
            await asyncio.sleep(0.5)


class MyOrchestrator(Orchestrator):
    def __init__(self, event_loop):
        super(MyOrchestrator, self).__init__(event_loop)

        producer = ProducerNode()
        consumer = ConsumerNode()

        self.add_nodes(producer, consumer)
        self.subscribe(consumer.producer_tag, producer, consumer)


run(MyOrchestrator)
