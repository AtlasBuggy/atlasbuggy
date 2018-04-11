import time
import random
import asyncio
from atlasbuggy import Orchestrator, Node, Message, run


class SomeMessage(Message):
    def __init__(self, n, timestamp=None):
        self.x = 0.0
        self.y = 0.0
        self.z = 0.0

        super(SomeMessage, self).__init__(n, timestamp)


class ProducerNode(Node):
    def __init__(self, enabled=True):
        super(ProducerNode, self).__init__(enabled)

    async def loop(self):
        counter = 0

        while True:
            msg = SomeMessage(counter)
            msg.x = random.random()
            msg.y = random.random()
            msg.z = random.random()

            await self.broadcast(msg)
            counter += 1

            await asyncio.sleep(0.5)
            self.logger.info("producer time: %s" % msg.timestamp)


class ConsumerNode(Node):
    def __init__(self, enabled=True):
        self.set_logger(write=False)
        super(ConsumerNode, self).__init__(enabled)

        self.producer_tag = "producer"
        self.producer_sub = self.define_subscription(self.producer_tag, message_type=SomeMessage, callback=self.msg_callback)
        self.producer = None

    def take(self):
        self.producer = self.producer_sub.get_producer()

        self.logger.info("Got producer named '%s'" % self.producer.name)

    def msg_callback(self, message):
        consumer_time = time.time()

        self.logger.info("time diff: %s" % (consumer_time - message.timestamp))
        self.logger.info("n: %s, x: %0.4f, y: %0.4f, z: %0.4f" % (message.n, message.x, message.y, message.z))

    # async def loop(self):
    #     while True:
    #         await asyncio.sleep(0.5)


class MyOrchestrator(Orchestrator):
    def __init__(self, event_loop):
        super(MyOrchestrator, self).__init__(event_loop)

        producer = ProducerNode()
        consumer = ConsumerNode()

        self.add_nodes(producer, consumer)
        self.subscribe(producer, consumer, consumer.producer_tag)


run(MyOrchestrator)
