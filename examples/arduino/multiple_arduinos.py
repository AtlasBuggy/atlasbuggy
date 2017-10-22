import os
import re
import time
import asyncio

from atlasbuggy.device import Arduino
from atlasbuggy import Node, Orchestrator, run


class FastArduinoMessage:
    _number = 0
    message_regex = r"sending: FastArduinoMessage\(t=(\d.*), at=(\d.*), n=(\d*), item1=(\d*), item2=(\d*)\)"
    start_message_regex = r"sending: FastArduinoMessage\(start_t=(\d.*)\)"

    def __init__(self, timestamp=None, arduino_time=None, item1=None, item2=None, n=None, arduino_start_time=None):
        self.timestamp = timestamp
        self.arduino_time = arduino_time
        self.arduino_start_time = arduino_start_time
        self.item1 = item1
        self.item2 = item2

        if n is None:
            self.number = FastArduinoMessage._number
            FastArduinoMessage._number += 1
        else:
            self.number = n

        if timestamp is None or arduino_time is None or item1 is None or item2 is None:
            self.is_initialization = True
        elif arduino_start_time is None:
            self.is_initialization = False
        else:
            raise ValueError("Invalid packet configuration: %s" % self)

    @classmethod
    def parse(clc, message):
        match = re.match(clc.message_regex, message)
        if match is not None:
            message_time = float(match.group(1))
            arduino_time = float(match.group(2))
            n = int(match.group(3))
            item1 = int(match.group(4))
            item2 = int(match.group(5))

            return FastArduinoMessage(message_time, arduino_time, item1, item2, n)
        else:
            match = re.match(clc.start_message_regex, message)
            if match is not None:
                arduino_start_time = float(match.group(1))
                return FastArduinoMessage(arduino_start_time=arduino_start_time)

        return None

    def __str__(self):
        return "%s(t=%s, at=%s, st=%s, n=%s, item1=%s, item2=%s)" % (
            self.__class__.__name__, self.timestamp, self.arduino_time, self.arduino_start_time, self.number,
            self.item1, self.item2)

    def average(self, *others):
        length = len(others)
        assert length > 0

        for other_message in others:
            self.item1 += other_message.item1
            self.item2 += other_message.item2

        self.item1 /= length
        self.item2 /= length


class SlowArduinoMessage:
    _number = 0
    message_regex = r"sending: SlowArduinoMessage\(t=(\d.*), at=(\d.*), st=(\d.*), n=(\d*), array=\[(?(1)(.+))\]\)"
    start_message_regex = r"sending: SlowArduinoMessage\(start_t=(\d.*)\)"

    def __init__(self, timestamp=None, arduino_time=None, array: list = None, n=None, arduino_start_time=None):
        self.timestamp = timestamp
        self.arduino_time = arduino_time
        self.arduino_start_time = arduino_start_time
        self.array = array

        if n is None:
            self.number = SlowArduinoMessage._number
            SlowArduinoMessage._number += 1
        else:
            self.number = n

        if timestamp is None or arduino_time is None or array is None:
            self.is_initialization = True
        elif arduino_start_time is None:
            self.is_initialization = False
        else:
            raise ValueError("Invalid packet configuration: %s" % self)

    @classmethod
    def parse(cls, message):
        match = re.match(cls.message_regex, message)
        if match is not None:
            message_time = float(match.group(1))
            arduino_time = float(match.group(2))
            n = int(match.group(3))
            array = [float(x) for x in match.group(4).split(", ")]

            return SlowArduinoMessage(message_time, arduino_time, array, n)
        else:
            match = re.match(cls.start_message_regex, message)
            if match is not None:
                arduino_start_time = float(match.group(1))

                return SlowArduinoMessage(arduino_start_time=arduino_start_time)

        return None

    def __str__(self):
        return "%s(t=%s, at=%s, st=%s n=%s, array=%s)" % (
            self.__class__.__name__, self.timestamp, self.arduino_time, self.arduino_start_time, self.number,
            self.array)


class FastArduino(Arduino):
    def __init__(self, enabled=True):
        super(FastArduino, self).__init__(
            self.name, enabled=enabled,
        )

    async def loop(self):
        arduino_start_time = self.start_time
        message = FastArduinoMessage(
            arduino_start_time=arduino_start_time
        )
        await self.broadcast([message])

        while self.device_active():
            while not self.device_read_queue.empty():
                packet_time, packets = self.device_read_queue.get()
                messages = []
                for packet in packets:
                    arduino_time, item1, item2 = [float(x) for x in packet.split("\t")]
                    message = FastArduinoMessage(
                        packet_time, arduino_time / 1000,
                        item1, item2
                    )

                    messages.append(message)
                self.log_to_buffer(packet_time, messages)
                await self.broadcast(messages)
            await asyncio.sleep(0.0)


class SlowArduino(Arduino):
    def __init__(self, enabled=True):
        super(SlowArduino, self).__init__(
            self.name, enabled=enabled,
        )

    async def loop(self):
        arduino_start_time = self.start_time
        message = SlowArduinoMessage(
            arduino_start_time=arduino_start_time
        )
        await self.broadcast(message)

        while self.device_active():
            while not self.device_read_queue.empty():
                packet_time, packets = self.device_read_queue.get()
                for packet in packets:
                    arduino_time, array = packet.split(";")
                    array = [int(x) for x in array.split(",")]
                    message = SlowArduinoMessage(
                        packet_time, float(arduino_time) / 1000,
                        array
                    )
                    self.log_to_buffer(packet_time, message)
                    await self.broadcast(message)
            await asyncio.sleep(0.0)


class AlgorithmNode(Node):
    def __init__(self, enabled=True):
        super(AlgorithmNode, self).__init__(enabled)

        self.fast_sensor_tag = "fast"
        self.fast_sensor_sub = self.define_subscription(self.fast_sensor_tag, message_type=list,
                                                        required_methods=("write",))
        self.fast_sensor_queue = None
        self.fast_sensor = None

        self.slow_sensor_tag = "slow"
        self.slow_sensor_sub = self.define_subscription(self.slow_sensor_tag, message_type=SlowArduinoMessage,
                                                        required_methods=("write",))
        self.slow_sensor_queue = None
        self.slow_sensor = None

        self.slow_avg_sum = 0
        self.slow_avg_count = 0

        self.fast_avg_sum = 0
        self.fast_avg_count = 0

        self.slow_min_delay = None
        self.slow_max_delay = None

        self.fast_min_delay = None
        self.fast_max_delay = None

    def take(self):
        self.fast_sensor_queue = self.fast_sensor_sub.get_queue()
        self.slow_sensor_queue = self.slow_sensor_sub.get_queue()

        self.fast_sensor = self.fast_sensor_sub.get_producer()
        self.slow_sensor = self.slow_sensor_sub.get_producer()

    async def loop(self):
        fast_prev_time = time.time()
        slow_prev_time = time.time()

        while True:
            fast_sensor_messages = []
            if self.fast_sensor_queue.empty():
                await asyncio.sleep(0.0)
                continue

            while not self.fast_sensor_queue.empty():
                messages = await self.fast_sensor_queue.get()
                for message in messages:
                    if message.is_initialization:
                        self.logger.info("got initialization message: %s" % message)
                    else:
                        consumer_time = time.time()
                        message_delay = consumer_time - message.timestamp
                        fast_sensor_messages.append(message)
                        self.fast_avg_sum += message_delay
                        self.fast_avg_count += 1
                        self.log_to_buffer(consumer_time, "got fast message: %s, delay: %s" % (message, message_delay))

                        if self.fast_max_delay is None or message_delay > self.fast_max_delay:
                            self.fast_max_delay = message_delay

                        if self.fast_min_delay is None or message_delay < self.fast_min_delay:
                            self.fast_min_delay = message_delay

            if len(fast_sensor_messages) > 1:
                fast_sensor_messages[0].average(*fast_sensor_messages[1:])
                fast_sensor_message = fast_sensor_messages[0]
                consumer_time = time.time()
                self.log_to_buffer(consumer_time, "average fast message: %s" % fast_sensor_message)

            slow_sensor_message = await self.slow_sensor_queue.get()
            if not slow_sensor_message.is_initialization:
                consumer_time = time.time()
                message_delay = consumer_time - slow_sensor_message.timestamp
                self.log_to_buffer(consumer_time,
                                   ("got slow message: %s, delay: %s" % (slow_sensor_message, message_delay)))

                if self.slow_max_delay is None or message_delay > self.slow_max_delay:
                    self.slow_max_delay = message_delay

                if self.slow_min_delay is None or message_delay < self.slow_min_delay:
                    self.slow_min_delay = message_delay

                self.slow_avg_sum += message_delay
                self.slow_avg_count += 1

            if time.time() - fast_prev_time > 0.15:
                self.fast_sensor.write("toggle")
                fast_prev_time = time.time()

            if time.time() - slow_prev_time > 0.15:
                self.slow_sensor.write("toggle")
                slow_prev_time = time.time()

    async def teardown(self):
        self.logger.info("fast arduino avg delay: %s, max: %s, min: %s" % (
            self.fast_avg_sum / self.fast_avg_count, self.fast_max_delay, self.fast_min_delay))
        self.logger.info("slow arduino avg delay: %s, max: %s, min: %s" % (
            self.slow_avg_sum / self.slow_avg_count, self.slow_max_delay, self.slow_min_delay))


class MyOrchestrator(Orchestrator):
    def __init__(self, event_loop):
        self.set_default(write=True, file_name="multiple_arduinos_demo.log",
                         directory=os.path.join("logs", "multiple_arduinos_demo", "%(name)s"))
        super(MyOrchestrator, self).__init__(event_loop)

        fast_sensor = FastArduino()
        slow_sensor = SlowArduino()
        algorithm = AlgorithmNode()

        self.add_nodes(fast_sensor, slow_sensor, algorithm)

        self.subscribe(algorithm.fast_sensor_tag, fast_sensor, algorithm)
        self.subscribe(algorithm.slow_sensor_tag, slow_sensor, algorithm)


if __name__ == '__main__':
    run(MyOrchestrator)
