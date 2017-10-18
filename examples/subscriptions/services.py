import time
import asyncio
from atlasbuggy import Orchestrator, Node, run


class ProducerNode(Node):
    def __init__(self, enabled=True):
        self.counter_service = "counter"
        super(ProducerNode, self).__init__(enabled)

    async def loop(self):
        counter = 0
        while True:
            producer_time = time.time()

            await self.broadcast(producer_time)
            await self.broadcast(counter, self.counter_service)

            counter += 1

            await asyncio.sleep(0.5)
            self.logger.info("producer time: %s" % producer_time)


class ConsumerNode1(Node):
    def __init__(self, enabled=True):
        super(ConsumerNode1, self).__init__(enabled)

        self.producer_tag = "producer"
        self.producer_sub = self.define_subscription(self.producer_tag)
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

            self.logger.info("time diff: %s" % (consumer_time - producer_time))
            await asyncio.sleep(0.5)


class ConsumerNode2(Node):
    def __init__(self, enabled=True):
        super(ConsumerNode2, self).__init__(enabled)

        self.producer_tag = "producer"
        self.producer_sub = self.define_subscription(self.producer_tag, service="counter")
        self.producer_queue = None
        self.producer = None

    def take(self):
        self.producer_queue = self.producer_sub.get_queue()
        self.producer = self.producer_sub.get_producer()

        self.logger.info("Got producer named '%s'" % self.producer.name)

    async def loop(self):
        while True:
            producer_counter = await self.producer_queue.get()

            self.logger.info("producer counter: %s" % producer_counter)
            await asyncio.sleep(0.5)


class MyOrchestrator(Orchestrator):
    def __init__(self, event_loop):
        super(MyOrchestrator, self).__init__(event_loop)

        producer = ProducerNode()
        consumer1 = ConsumerNode1()
        consumer2 = ConsumerNode2()

        self.add_nodes(producer, consumer1, consumer2)

        self.subscribe(consumer1.producer_tag, producer, consumer1)
        self.subscribe(consumer2.producer_tag, producer, consumer2)


run(MyOrchestrator)
