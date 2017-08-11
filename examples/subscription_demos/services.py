import random
import struct
from atlasbuggy import Robot, AsyncStream
from atlasbuggy.subscriptions import *
import asyncio


class FloatGenerator(AsyncStream):
    def __init__(self, enabled=True):
        super(FloatGenerator, self).__init__(enabled, log_level=20)

        self.hex_byte_service_tag = "hex_byte"  # the tag to use when specifying this service
        self.add_service(self.hex_byte_service_tag)  # define this as a service in addition to "default"

        # producers can also be subscribed to streams that consume its resources
        # let's use this resource when generating the random floating point numbers
        self.multiplier_tag = "multiplier"
        self.multiplier_feed = None
        self.require_subscription(self.multiplier_tag, Feed)

    def take(self, subscriptions):
        self.multiplier_feed = subscriptions[self.multiplier_tag].get_feed()

    async def generate_random_float(self):
        """Generate a random float using numbers from the multiplier subscription"""
        if self.multiplier_feed.empty():  # if there's no data available, use 1.0
            multiplier = 1.0
            self.logger.info("Using default multiplier")
        else:
            multiplier = await self.multiplier_feed.get()  # get the multiplier
            self.multiplier_feed.task_done()  # free up the queue

            self.logger.info("Using %s as the multiplier" % multiplier)

        return random.random() * multiplier  # generate a random number using the multiplier

    async def run(self):
        while self.is_running():
            # generate a random number
            number = await self.generate_random_float()

            # post the random number
            await self.post(number)
            self.logger.info("Posted %0.4f" % number)

            # generate the hex representation of the number and post it
            hex_bytes = self.float_to_hex(number)
            await self.post(hex_bytes, self.hex_byte_service_tag)
            self.logger.info("Posted %s" % hex_bytes)

            # don't spam the feed so much so we can see what's happening
            await asyncio.sleep(0.5)

    @staticmethod
    def float_to_hex(f):
        """Convert a floating point number into its hex representation"""

        float_bytes = struct.pack('<f', f)  # convert float to byte representation
        integer = struct.unpack('<I', float_bytes)[0]  # convert bytes to int
        return "0x%08x" % integer  # format integer as a hex string with 8 trailing zeros


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
    def __init__(self, enabled=True):
        super(HexByteConsumer, self).__init__(enabled, log_level=20)

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
    def __init__(self, enabled=True):
        super(HexAndFloatConsumer, self).__init__(enabled, log_level=20)

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


def run():
    robot = Robot(write=False)

    float_generator = FloatGenerator()
    float_consumer = FloatConsumer()
    hex_byte_consumer = HexByteConsumer()
    float_and_hex_consumer = HexAndFloatConsumer(enabled=False)

    float_consumer.subscribe(Feed(
        float_consumer.float_generator_tag,
        float_generator
    ))
    hex_byte_consumer.subscribe(Feed(
        hex_byte_consumer.float_generator_tag,
        float_generator,
        hex_byte_consumer.hex_byte_service_tag
    ))
    # float_and_hex_consumer.subscribe(Feed(
    #     float_and_hex_consumer.float_tag,
    #     float_generator
    # ))
    # float_and_hex_consumer.subscribe(Feed(
    #     float_and_hex_consumer.hex_tag,
    #     float_generator,
    #     float_and_hex_consumer.hex_byte_service_tag
    # ))

    float_generator.subscribe(Feed(
        float_generator.multiplier_tag, float_consumer
    ))

    robot.run(float_generator, float_consumer, hex_byte_consumer, float_and_hex_consumer)


run()
