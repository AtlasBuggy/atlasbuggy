import time
import asyncio
from atlasbuggy import Orchestrator, Node, run


class Node1(Node):
    def __init__(self, enabled=True):
        super(Node1, self).__init__(enabled)

    async def loop(self):
        while True:
            producer_time = time.time()
            await self.broadcast(producer_time)
            self.logger.info("broadcasting: %s" % producer_time)
            await asyncio.sleep(0.5)


class Node2(Node):
    def __init__(self, enabled=True):
        super(Node2, self).__init__(enabled)

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

            await self.broadcast(producer_time)

            self.logger.info("middle time diff: %s" % (consumer_time - producer_time))
            await asyncio.sleep(0.5)


class Node3(Node):
    def __init__(self, enabled=True):
        super(Node3, self).__init__(enabled)

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

            # self.logger.info("producer time: %s, consumer time: %s" % (producer_time, consumer_time))
            self.logger.info("end time diff: %s" % (consumer_time - producer_time))
            await asyncio.sleep(0.5)


class MyOrchestrator(Orchestrator):
    def __init__(self, event_loop):
        super(MyOrchestrator, self).__init__(event_loop)

        node1 = Node1()
        node2 = Node2()
        node3 = Node3()

        self.add_nodes(node1, node2, node3)

        self.subscribe(node1, node2, node2.producer_tag)
        self.subscribe(node2, node3, node3.producer_tag)


run(MyOrchestrator)
