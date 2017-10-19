import time
import asyncio

from device import Arduino
from atlasbuggy import Orchestrator, Node, run


class MyArduino(Arduino):
    def __init__(self, enabled=True):
        self.buffer = ""
        super(MyArduino, self).__init__(
            self.name, enabled=enabled,
            logger=self.make_logger(level=30)
        )

    async def loop(self):
        arduino_start_time = 0
        # start_time = time.time()
        counter = 0
        while self.device_active():
            while not self.device_read_queue.empty():
                packet_time, packet = self.device_read_queue.get()
                if packet_time < 0:

                    self.logger.info("initialization data: %s. Start time: %s" % (packet, arduino_start_time))
                    arduino_start_time = -packet_time

                    self.logger.info("Start time: %s" % arduino_start_time)
                else:
                    arduino_time, item1, item2 = [float(x) for x in packet.split("\t")]
                    # self.log_to_buffer(20, time.time(), "t=%s, item1=%s, item2=%s" % (arduino_time, item1, item2))

                    # if counter % 1000 == 0 and counter > 0:
                    #     self.logger.info(self.buffer)

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
        # self.messages = []

        while True:
            while not self.producer_queue.empty():
                counter, packet_time, arduino_time, arduino_start_time, item1, item2 = self.producer_queue.get_nowait()
                consumer_time = time.time()

                # self.logger.info("------ got packet #%s ------" % counter)
                # self.log_to_buffer(20, packet_time, "receive time diff: %s" % (consumer_time - packet_time))
                # self.logger.info("arduino time diff: %s" % ((consumer_time - arduino_start_time) - arduino_time))

                # self.logger.info("arduino time: %s, consumer time: %s" % (arduino_time, consumer_time - arduino_start_time))
                # self.logger.info("item1=%s, item2=%s" % (item1, item2))

                self.avg_time_sum += consumer_time - packet_time
                self.avg_count += 1

            await asyncio.sleep(0.0)

    async def teardown(self):
        # for message in self.messages:
        #     self.logger.info(message)
        print(self.avg_time_sum / self.avg_count)


class MyOrchestrator(Orchestrator):
    def __init__(self, event_loop):
        super(MyOrchestrator, self).__init__(event_loop)

        my_arduino = MyArduino()
        consumer = ConsumerNode()

        self.add_nodes(my_arduino, consumer)
        self.subscribe(consumer.producer_tag, my_arduino, consumer)


run(MyOrchestrator)
