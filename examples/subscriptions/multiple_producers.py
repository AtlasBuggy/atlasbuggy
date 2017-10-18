import os
import re
import time
import random
import asyncio

from atlasbuggy import Node, Orchestrator, run


class FastSensorMessage:
    _number = 0
    message_regex = r"sending: FastSensorMessage\(t=(\d.*), n=(\d*), x=(\d.*), y=(\d.*), z=(\d.*)\)"

    def __init__(self, timestamp, x=0.0, y=0.0, z=0.0, n=None):
        self.timestamp = timestamp
        self.x = x
        self.y = y
        self.z = z

        if n is None:
            self.number = FastSensorMessage._number
            FastSensorMessage._number += 1
        else:
            self.number = n

    @classmethod
    def parse(clc, message):
        match = re.match(clc.message_regex, message)
        if match is not None:
            message_time = float(match.group(1))
            n = int(match.group(2))
            x = float(match.group(3))
            y = float(match.group(4))
            z = float(match.group(5))

            return FastSensorMessage(message_time, x, y, z, n)
        else:
            return None

    def __str__(self):
        return "%s(t=%s, n=%s, x=%s, y=%s, z=%s)" % (
            self.__class__.__name__, self.timestamp, self.number, self.x, self.y, self.z)

    def average(self, *others):
        length = len(others)
        assert length > 0

        for other_message in others:
            self.x += other_message.x
            self.y += other_message.y
            self.z += other_message.z

        self.x /= length
        self.y /= length
        self.z /= length


class SlowSensorMessage:
    _number = 0
    message_regex = r"(sending: SlowSensorMessage\(t=([\d.]*)), n=(\d*), array=\[(?(1)(.+))\]\)"

    def __init__(self, timestamp, array: list, n=None):
        self.timestamp = timestamp
        self.array = array

        if n is None:
            self.number = SlowSensorMessage._number
            SlowSensorMessage._number += 1
        else:
            self.number = n

    @classmethod
    def parse(cls, message):
        match = re.match(cls.message_regex, message)
        if match is not None:
            message_time = float(match.group(2))
            n = int(match.group(3))
            array = [float(x) for x in match.group(4).split(", ")]

            return SlowSensorMessage(message_time, array, n)
        else:
            return None

    def __str__(self):
        return "%s(t=%s, n=%s, array=%s)" % (
            self.__class__.__name__, self.timestamp, self.number, self.array)


class FastSensor(Node):
    def __init__(self, enabled=True):
        super(FastSensor, self).__init__(enabled)

    async def loop(self):
        current_time = time.time()
        delta_t = 0.01
        while True:
            if time.time() > current_time + delta_t:  # simulate update rate of 100 Hz
                current_time = time.time()
                message = FastSensorMessage(
                    current_time,
                    random.random(), random.random(), random.random()
                )
                self.logger.info("sending: %s" % message)
                await self.broadcast(message)
            else:
                await asyncio.sleep(0.0)


class SlowSensor(Node):
    def __init__(self, enabled=True):
        super(SlowSensor, self).__init__(enabled)

    async def loop(self):
        current_time = time.time()
        delta_t = 0.1
        while True:
            if time.time() > current_time + delta_t:  # simulate update rate of 10 Hz
                current_time = time.time()
                message = SlowSensorMessage(
                    time.time(),
                    [random.randint(0, 2 ** 16) for _ in range(100)]
                )
                self.logger.info("sending: %s" % message)
                await self.broadcast(message)
            else:
                await asyncio.sleep(0.0)


class AlgorithmNode(Node):
    def __init__(self, enabled=True):
        super(AlgorithmNode, self).__init__(enabled)

        self.fast_sensor_tag = "fast"
        self.fast_sensor_sub = self.define_subscription(self.fast_sensor_tag, message_type=FastSensorMessage)
        self.fast_sensor_queue = None

        self.slow_sensor_tag = "slow"
        self.slow_sensor_sub = self.define_subscription(self.slow_sensor_tag, message_type=SlowSensorMessage)
        self.slow_sensor_queue = None

    def take(self):
        self.fast_sensor_queue = self.fast_sensor_sub.get_queue()
        self.slow_sensor_queue = self.slow_sensor_sub.get_queue()

    async def loop(self):
        while True:
            fast_sensor_messages = []
            if self.fast_sensor_queue.empty():
                await asyncio.sleep(0.0)
                continue

            while not self.fast_sensor_queue.empty():
                fast_sensor_messages.append(await self.fast_sensor_queue.get())

            if len(fast_sensor_messages) > 1:
                # 100 Hz / 10 Hz = 10 fast sensor messages to every 1 slow message
                if len(fast_sensor_messages) != 10:
                    self.logger.warning("Received %s fast sensor messages as opposed to 10!" % len(fast_sensor_messages))
                self.logger.info("averaging fast %s messages" % len(fast_sensor_messages))
                fast_sensor_messages[0].average(*fast_sensor_messages[1:])

            fast_sensor_message = fast_sensor_messages[0]
            self.logger.info("got fast messages: %s" % fast_sensor_message)

            slow_sensor_message = await self.slow_sensor_queue.get()
            self.logger.info("got slow message: %s" % slow_sensor_message)


class MyOrchestrator(Orchestrator):
    def __init__(self, event_loop):
        self.set_default(write=True, file_name="multiple_producers_demo.log",
                         directory=os.path.join("logs", "multiple_producers_demo", "%(name)s"))

        super(MyOrchestrator, self).__init__(event_loop)

        fast_sensor = FastSensor()
        slow_sensor = SlowSensor()
        algorithm = AlgorithmNode()

        self.add_nodes(fast_sensor, slow_sensor, algorithm)

        self.subscribe(algorithm.fast_sensor_tag, fast_sensor, algorithm)
        self.subscribe(algorithm.slow_sensor_tag, slow_sensor, algorithm)

        self.t0 = 0
        self.t1 = 0

    async def setup(self):
        self.t0 = time.time()

    async def teardown(self):
        self.t1 = time.time()

        print("took: %ss" % (self.t1 - self.t0))

if __name__ == '__main__':
    run(MyOrchestrator)
