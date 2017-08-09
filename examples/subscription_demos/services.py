import random
import struct
from atlasbuggy import Robot, AsyncStream
from atlasbuggy.subscriptions import *
import asyncio


class FloatGenerator(AsyncStream):
    def __init__(self):
        super(FloatGenerator, self).__init__(log_level=20)

        self.hex_byte_service_tag = "hex_byte"
        self.add_service(self.hex_byte_service_tag)

        self.multiplier_tag = "multiplier"
        self.multiplier_feed = None
        self.require_subscription(self.multiplier_tag, Feed)

    def take(self, subscriptions):
        self.multiplier_feed = subscriptions[self.multiplier_tag].get_feed()

    async def run(self):
        while self.is_running():
            if self.multiplier_feed.empty():
                multiplier = 1.0
                self.logger.info("Using default multiplier")
            else:
                multiplier = await self.multiplier_feed.get()
                self.multiplier_feed.task_done()
                self.logger.info("Using %s as the multiplier" % multiplier)
            number = random.random() * multiplier
            await self.post(number)
            self.logger.info("Posted %0.4f" % number)

            hex_bytes = self.float_to_hex(number)
            await self.post(hex_bytes, self.hex_byte_service_tag)
            self.logger.info("Posted %s" % hex_bytes)

            await asyncio.sleep(0.01)

    @staticmethod
    def float_to_hex(f):
        return hex(struct.unpack('<I', struct.pack('<f', f))[0])


class FloatConsumer(AsyncStream):
    def __init__(self):
        super(FloatConsumer, self).__init__(log_level=20)

        self.float_generator_tag = "float_generator"
        self.float_generator_feed = None
        self.require_subscription(self.float_generator_tag, Feed)

    def take(self, subscriptions):
        self.float_generator_feed = subscriptions[self.float_generator_tag].get_feed()

    async def run(self):
        while self.is_running():
            while not self.float_generator_feed.empty():
                await self.get_number()
                self.float_generator_feed.task_done()
            await asyncio.sleep(0.01)

    async def get_number(self):
        number = await self.float_generator_feed.get()
        self.logger.info("Got number: '%s'" % number)
        await self.post(100.0)


class HexByteConsumer(AsyncStream):
    def __init__(self):
        super(HexByteConsumer, self).__init__(log_level=20)

        self.float_generator_tag = "float_generator"
        self.float_generator_feed = None
        self.hex_byte_service_tag = "hex_byte"
        self.require_subscription(self.float_generator_tag, Feed, service_tag=self.hex_byte_service_tag)

    def take(self, subscriptions):
        self.float_generator_feed = subscriptions[self.float_generator_tag].get_feed()

    async def run(self):
        while self.is_running():
            while not self.float_generator_feed.empty():
                await self.get_hex_byte()
                self.float_generator_feed.task_done()
            await asyncio.sleep(0.01)

    async def get_hex_byte(self):
        number = await self.float_generator_feed.get()
        self.logger.info("Got hex: '%s'" % number)
        await self.post(1000.0)


class HexAndFloatConsumer(AsyncStream):
    def __init__(self):
        super(HexAndFloatConsumer, self).__init__(log_level=20)

        self.float_tag = "float"
        self.float_feed = None
        self.require_subscription(self.float_tag, Feed)

        self.hex_tag = "hex"
        self.hex_feed = None
        self.hex_byte_service_tag = "hex_byte"
        self.require_subscription(self.hex_tag, Feed, service_tag=self.hex_byte_service_tag)

    def take(self, subscriptions):
        self.float_feed = subscriptions[self.float_tag].get_feed()
        self.hex_feed = subscriptions[self.hex_tag].get_feed()

    async def run(self):
        while self.is_running():
            while not self.float_feed.empty():
                await self.get_float()
                self.float_feed.task_done()

            while not self.hex_feed.empty():
                await self.get_hex()
                self.hex_feed.task_done()
            await asyncio.sleep(0.01)

    async def get_float(self):
        number = await self.float_feed.get()
        self.logger.info("Got float: '%s'" % number)
        await self.post(number * 1000)

    async def get_hex(self):
        hex_byte = await self.hex_feed.get()
        self.logger.info("Got hex byte: '%s'" % hex_byte)


robot = Robot(write=False, log_level=10)

float_generator = FloatGenerator()
float_consumer = FloatConsumer()
hex_byte_consumer = HexByteConsumer()
float_and_hex_consumer = HexAndFloatConsumer()

float_consumer.subscribe(
    Feed(float_consumer.float_generator_tag, float_generator)
)
hex_byte_consumer.subscribe(
    Feed(hex_byte_consumer.float_generator_tag, float_generator, hex_byte_consumer.hex_byte_service_tag)
)
float_and_hex_consumer.subscribe(
    Feed(float_and_hex_consumer.float_tag, float_generator)
)
float_and_hex_consumer.subscribe(
    Feed(float_and_hex_consumer.hex_tag, float_generator, float_and_hex_consumer.hex_byte_service_tag)
)

float_generator.subscribe(
    Feed(float_generator.multiplier_tag, float_consumer)
)

robot.run(float_generator, float_consumer, hex_byte_consumer, float_and_hex_consumer)
