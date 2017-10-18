import unittest

import time
import asyncio
from atlasbuggy import Orchestrator, Node, run_orchestrator


class ProducerNode(Node):
    def __init__(self, enabled=True):
        super(ProducerNode, self).__init__(enabled)

    async def loop(self):
        while True:
            self.logger.info("loop: broadcasting time")
            producer_time = time.time()
            await self.broadcast(producer_time)
            await asyncio.sleep(0.5)
            self.logger.info("producer time: %s" % producer_time)


class ConsumerNode(Node):
    def __init__(self, enabled=True):
        super(ConsumerNode, self).__init__(enabled)

        self.producer_sub = self.define_subscription()
        self.producer_queue = None
        self.producer = None

    def take(self):
        self.producer_queue = self.producer_sub.get_queue()
        self.producer = self.producer_sub.get_producer()

        self.logger.info("Got producer named '%s'" % self.producer.name)

    async def loop(self):
        while True:
            self.logger.info("loop: getting time")
            producer_time = await self.producer_queue.get()
            consumer_time = time.time()

            self.logger.info("producer time: %s, consumer time: %s, qsize: %s" % (
                producer_time, consumer_time, self.producer_queue.qsize()))
            self.logger.info("time diff: %s" % (consumer_time - producer_time))
            await asyncio.sleep(0.5)


class MyOrchestrator(Orchestrator):
    def __init__(self, event_loop):
        super(MyOrchestrator, self).__init__(event_loop)

        self.producer = ProducerNode()
        self.consumer = ConsumerNode()


class TestSubscriptions(unittest.TestCase):
    def test_self_subscription(self):
        print("test_self_subscription")
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        orchestrator = MyOrchestrator(loop)

        orchestrator.add_nodes(orchestrator.producer, orchestrator.consumer)
        try:
            orchestrator.subscribe(orchestrator.producer, orchestrator.producer)
        except ValueError:
            print("made it!")

    def test_no_nodes_added(self):
        print("no_nodes_added")
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        orchestrator = MyOrchestrator(loop)

        try:
            orchestrator.subscribe(orchestrator.producer, orchestrator.producer)
        except RuntimeError:
            print("made it!")


if __name__ == '__main__':
    unittest.main()
