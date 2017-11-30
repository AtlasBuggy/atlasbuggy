import time
import asyncio
from atlasbuggy import Orchestrator, Node, run


class ProducerNode(Node):
    def __init__(self, enabled=True):
        super(ProducerNode, self).__init__(enabled)

        self.counter_service = "counter"
        self.define_service(self.counter_service, int)

    async def loop(self):
        counter = 0
        while True:
            producer_time = time.time()

            await self.broadcast(producer_time)
            await self.broadcast(counter, self.counter_service)

            counter += 1

            await asyncio.sleep(0.5)
            self.logger.info("producer time: %s" % producer_time)


class NoServiceTagConsumer(Node):
    def __init__(self, enabled=True):
        super(NoServiceTagConsumer, self).__init__(enabled)

        self.time_producer_tag = "time"
        self.time_producer_sub = self.define_subscription(self.time_producer_tag)
        self.time_producer_queue = None

        self.counter_producer_tag = "counter"
        self.counter_producer_sub = self.define_subscription(self.counter_producer_tag)
        self.counter_producer_queue = None

    def take(self):
        self.time_producer_queue = self.time_producer_sub.get_queue()
        self.counter_producer_queue = self.counter_producer_sub.get_queue()

    async def loop(self):
        while True:
            producer_time = await self.time_producer_queue.get()
            consumer_time = time.time()

            self.logger.info("time diff: %s" % (consumer_time - producer_time))

            counter = await self.counter_producer_queue.get()
            self.logger.info("counter: %s" % counter)

            await asyncio.sleep(0.5)

class ServiceTagConsumer(Node):
    def __init__(self, enabled=True):
        super(ServiceTagConsumer, self).__init__(enabled)

        self.time_producer_tag = "time"
        self.time_service = "default"
        self.time_producer_sub = self.define_subscription(self.time_producer_tag, self.time_service)
        self.time_producer_queue = None

        self.counter_producer_tag = "counter"
        self.counter_service = "counter"
        self.counter_producer_sub = self.define_subscription(self.counter_producer_tag, self.counter_service)
        self.counter_producer_queue = None

    def take(self):
        self.time_producer_queue = self.time_producer_sub.get_queue()
        self.counter_producer_queue = self.counter_producer_sub.get_queue()

    async def loop(self):
        while True:
            producer_time = await self.time_producer_queue.get()
            consumer_time = time.time()

            self.logger.info("time diff: %s" % (consumer_time - producer_time))

            counter = await self.counter_producer_queue.get()
            self.logger.info("counter: %s" % counter)

            await asyncio.sleep(0.5)


class MyOrchestrator(Orchestrator):
    def __init__(self, event_loop):
        super(MyOrchestrator, self).__init__(event_loop)

        producer = ProducerNode()
        consumer1 = NoServiceTagConsumer()
        consumer2 = ServiceTagConsumer()

        self.add_nodes(producer, consumer1, consumer2)

        self.subscribe(producer, consumer1, consumer1.time_producer_tag)
        self.subscribe(producer, consumer1, consumer1.counter_producer_tag, producer.counter_service)

        self.subscribe(producer, consumer2, consumer2.time_producer_tag)
        self.subscribe(producer, consumer2, consumer2.counter_producer_tag)


run(MyOrchestrator)
