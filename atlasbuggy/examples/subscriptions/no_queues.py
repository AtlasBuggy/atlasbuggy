import time
import asyncio
from atlasbuggy import Orchestrator, Node, run


DEMONSTRATE_ERROR = False


class ProducerNode(Node):
    def __init__(self, enabled=True):
        super(ProducerNode, self).__init__(enabled)

    async def loop(self):
        while True:
            self.logger.info("idling")
            self.logger.info("producer time: %s" % time.time())
            await asyncio.sleep(1)

    def do_a_thing(self):
        self.logger.info("doing a thing")

    def do_another_thing(self):
        self.logger.info("doing another thing")

    def do_yet_another_thing(self):
        self.logger.info("doing yet another thing")


class ConsumerNode(Node):
    def __init__(self, enabled=True):
        super(ConsumerNode, self).__init__(enabled)

        self.producer_tag = "producer"
        self.producer_sub = self.define_subscription(self.producer_tag, queue_size=None)
        self.producer_queue = None
        self.producer = None

    def take(self):
        if DEMONSTRATE_ERROR:
            self.producer_queue = self.producer_sub.get_queue()
        self.producer = self.producer_sub.get_producer()

        self.logger.info("Got producer named '%s'" % self.producer.name)

    async def loop(self):
        while True:
            self.logger.info("making producer do a thing")
            self.producer.do_a_thing()
            await asyncio.sleep(0.5)

            self.logger.info("making producer do another thing")
            self.producer.do_another_thing()
            await asyncio.sleep(0.5)

            self.logger.info("making producer do yet another thing")
            self.producer.do_yet_another_thing()
            await asyncio.sleep(0.5)


class MyOrchestrator(Orchestrator):
    def __init__(self, event_loop):
        self.set_default(level=10)
        super(MyOrchestrator, self).__init__(event_loop)

        producer = ProducerNode()
        consumer = ConsumerNode()

        self.add_nodes(producer, consumer)
        self.subscribe(producer, consumer, consumer.producer_tag)


run(MyOrchestrator)
