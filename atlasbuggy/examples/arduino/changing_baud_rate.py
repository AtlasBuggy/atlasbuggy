import os
import time
import asyncio

from atlasbuggy.device import Arduino
from atlasbuggy import Orchestrator, Node, run


class DiffBaudArduino(Arduino):
    def __init__(self, enabled=True):
        super(DiffBaudArduino, self).__init__(
            self.name,
            baud=9600,
            enabled=enabled,
        )
        self.set_logger(write=True, file_name="changing_baud_rate_demo.log",
                        directory=os.path.join("logs", "changing_baud_rate_demo", "%(name)s"))
        self.max_log_buf_size = 1024

    async def loop(self):
        arduino_start_time = self.start_time
        counter = 0
        self.logger.info("initialization data: %s. Start time: %s" % (self.first_packet, arduino_start_time))

        while self.device_active():
            while not self.empty():
                packet_time, packet = self.read()
                arduino_time, item1, item2 = [float(x) for x in packet.split("\t")]
                self.log_to_buffer(time.time(), "t=%s, item1=%s, item2=%s" % (arduino_time, item1, item2))

                await self.broadcast((counter, packet_time, arduino_time / 1000, arduino_start_time, item1, item2))
                counter += 1

            await asyncio.sleep(0.0)


class ConsumerNode(Node):
    def __init__(self, enabled=True):
        super(ConsumerNode, self).__init__(enabled)

        self.producer_tag = "producer"
        self.producer_sub = self.define_subscription(self.producer_tag)
        self.producer_queue = None
        self.producer = None

        self.avg_time_sum = 0
        self.avg_count = 0

    def take(self):
        self.producer_queue = self.producer_sub.get_queue()
        self.producer = self.producer_sub.get_producer()

        self.logger.info("Got producer named '%s'" % self.producer.name)

    async def loop(self):

        while True:
            while not self.producer_queue.empty():
                counter, packet_time, arduino_time, arduino_start_time, item1, item2 = self.producer_queue.get_nowait()
                consumer_time = time.time()

                self.avg_time_sum += consumer_time - packet_time
                self.avg_count += 1

            await asyncio.sleep(0.0)

    async def teardown(self):
        self.logger.info("average packet delay: %s" % (self.avg_time_sum / self.avg_count))


class MyOrchestrator(Orchestrator):
    def __init__(self, event_loop):
        super(MyOrchestrator, self).__init__(event_loop)

        my_arduino = DiffBaudArduino()
        consumer = ConsumerNode()

        self.add_nodes(my_arduino, consumer)
        self.subscribe(my_arduino, consumer, consumer.producer_tag)


if __name__ == '__main__':
    run(MyOrchestrator)
