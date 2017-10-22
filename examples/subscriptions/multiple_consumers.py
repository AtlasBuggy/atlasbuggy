import time
import asyncio
from atlasbuggy import Orchestrator, Node, run


class ProducerNode(Node):
    def __init__(self, enabled=True):
        super(ProducerNode, self).__init__(enabled)

    async def loop(self):
        while True:
            self.logger.info("loop: broadcasting time")
            producer_time = time.time()
            await self.broadcast(producer_time)
            await asyncio.sleep(0.5)


class ConsumerNode(Node):
    def __init__(self, consumer_num, enabled=True):
        super(ConsumerNode, self).__init__(enabled, self.__class__.__name__ + str(consumer_num))

        self.consumer_num = consumer_num
        self.producer_tag = "producer"
        self.producer_sub = self.define_subscription(self.producer_tag, message_type=float)
        self.producer_queue = None
        self.producer = None

    def take(self):
        self.producer_queue = self.producer_sub.get_queue()
        self.producer = self.producer_sub.get_producer()

        self.logger.info("Got producer named '%s'" % self.producer.name)

    async def loop(self):
        while True:
            producer_time = await self.producer_queue.get()
            consumer_time = time.time()

            self.logger.info("Consumer #%s: time diff: %s" % (self.consumer_num, consumer_time - producer_time))
            await asyncio.sleep(0.5)


class MyOrchestrator(Orchestrator):
    def __init__(self, event_loop):
        super(MyOrchestrator, self).__init__(event_loop)

        producer = ProducerNode()
        consumers = []
        for consumer_num in range(10):
            consumer = ConsumerNode(consumer_num)
            consumers.append(consumer)

        self.add_nodes(producer, *consumers)
        for consumer in consumers:
            self.subscribe(producer, consumer, consumer.producer_tag)


run(MyOrchestrator)
