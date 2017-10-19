import time
import random
import asyncio
import multiprocessing

from atlasbuggy import Orchestrator, Node, run


class MainThreadHogger(Node):
    def __init__(self, enabled=True):
        super(MainThreadHogger, self).__init__(enabled)

    async def loop(self):
        while True:
            self.logger.info("loop: broadcasting time")
            producer_time = time.time()

            counter = 0

            # stalls the whole main thread
            t0 = time.time()
            while time.time() - t0 < 1:
                counter += 1
            await self.broadcast((producer_time, counter))

            await asyncio.sleep(0.5)
            self.logger.info("producer time: %s" % producer_time)


DEMO_EXCEPTION_IN_PROCESS = False


class OffloadWithProcess(Node):
    def __init__(self, enabled=True):
        self.exit_event = multiprocessing.Event()
        self.read_queue = multiprocessing.Queue()
        self.write_queue = multiprocessing.Queue()
        self.process = multiprocessing.Process(target=self.process_fn)

        super(OffloadWithProcess, self).__init__(enabled)

    def process_fn(self):
        time_to_wait = 1
        while not self.exit_event.is_set():
            process_time = time.time()

            counter = 0
            t0 = time.time()

            while time.time() - t0 < time_to_wait:
                counter += 1
                self.read_queue.put((process_time, counter))
                # time.sleep(0.0001)
                time.sleep(time_to_wait / 5)
                if self.exit_event.is_set():
                    break

            while not self.write_queue.empty():
                time_to_wait = self.write_queue.get()

            if DEMO_EXCEPTION_IN_PROCESS:
                self.exit_event.set()
                raise Exception("Something bad happened!!")

            self.logger.info("Process put %s items on the pipe" % counter)

    async def setup(self):
        self.process.start()

    async def loop(self):
        message_num = 0
        while True:
            if self.exit_event.is_set():
                return

            counter = 0
            while not self.read_queue.empty():
                process_time, counter = self.read_queue.get()
                producer_time = time.time()
                self.broadcast_nowait((message_num, producer_time, process_time, counter))
                counter += 1
                message_num += 1

            time_to_wait = random.random()
            self.logger.info("set time to wait: %s" % time_to_wait)
            self.write_queue.put(time_to_wait)

            if counter > 0:
                self.logger.info("broadcast %s items, last num was %s" % (counter, message_num))
            await asyncio.sleep(0.5)

    async def teardown(self):
        self.logger.info("closing process")
        self.exit_event.set()


class ConsumerNode(Node):
    def __init__(self, enabled=True):
        super(ConsumerNode, self).__init__(enabled)

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
            if not self.producer_queue.empty():
                self.logger.info("Consuming %s items" % self.producer_queue.qsize())
                while not self.producer_queue.empty():
                    message_num, producer_time, process_time, counter = self.producer_queue.get_nowait()
                    consumer_time = time.time()

                    self.logger.info(
                        "n: %s, process time: %s, qsize: %s, counter: %s" % (
                            message_num, process_time, self.producer_queue.qsize(),
                            counter))
                    self.logger.info("time diff: %s" % (consumer_time - producer_time))
            await asyncio.sleep(0.0)


class MyOrchestrator(Orchestrator):
    def __init__(self, event_loop):
        super(MyOrchestrator, self).__init__(event_loop)

        # producer = MainThreadHogger()
        producer = OffloadWithProcess()
        consumer = ConsumerNode()

        self.add_nodes(producer, consumer)
        self.subscribe(consumer.producer_tag, producer, consumer)


run(MyOrchestrator)
