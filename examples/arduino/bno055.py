import os
import re
import time
import math
import asyncio

from atlasbuggy.device import Arduino
from atlasbuggy import Orchestrator, Node, Message, run


class Bno055Vector:
    def __init__(self, name, *vector):
        self.name = name
        self.x = 0.0
        self.y = 0.0
        self.z = 0.0
        self.w = 0.0

        if len(vector) >= 1:
            self.x = vector[0]
        if len(vector) >= 2:
            self.y = vector[1]
        if len(vector) >= 3:
            self.z = vector[2]
        if len(vector) >= 4:
            self.w = vector[3]

    def __getitem__(self, item):
        if type(item) == int:
            if item == 0:
                return self.x
            elif item == 1:
                return self.y
            elif item == 2:
                return self.z
            elif item == 3:
                return self.w
        else:
            return self.__dict__[item]

    def __setitem__(self, item, value):
        if type(item) == int:
            if item == 0:
                self.x = value
            elif item == 1:
                self.y = value
            elif item == 2:
                self.z = value
            elif item == 3:
                self.w = value
        else:
            self.__dict__[item] = value

    def get_tuple(self, xyz=True):
        if xyz:
            return self.x, self.y, self.z
        else:
            return self.x, self.y, self.z, self.w


class Bno055Message(Message):
    message_regex = r"t: (\d.*), pt: (\d.*), at: (\d.*), n: (\d*), " \
                    r"euler: \(([-\d., ]*)\), " \
                    r"mag: \(([-\d., ]*)\), gyro: \(([-\d., ]*)\), accel: \(([-\d., ]*)\), " \
                    r"linaccel: \(([-\d., ]*)\), quat: \(([-\d., ]*)\)"

    def __init__(self, timestamp, n=None):
        self.packet_time = 0.0
        self.arduino_time = 0.0
        self.euler = Bno055Vector("euler")
        self.mag = Bno055Vector("mag")
        self.gyro = Bno055Vector("gyro")
        self.accel = Bno055Vector("accel")
        self.linaccel = Bno055Vector("linaccel")
        self.quat = Bno055Vector("quat")

        self.vectors = [self.euler, self.mag, self.gyro, self.accel, self.linaccel, self.quat]
        # self.vectors_dict = {self.euler.name: self.euler, self.mag.name: self.mag, self.gyro.name: self.gyro,
        #                      self.accel.name: self.accel, self.linaccel.name: self.linaccel}

        self.system_status = 0
        self.accel_status = 0
        self.gyro_status = 0
        self.mag_status = 0

        super(Bno055Message, self).__init__(timestamp, n)

    def __str__(self):
        string = "t: %s, pt: %s, at: %s, n: %s, " % (self.timestamp, self.packet_time, self.arduino_time, self.n)
        for vector in self.vectors[:-1]:
            string += "%s: %s, " % (vector.name, vector.get_tuple())

        string += "%s: %s" % (self.quat.name, self.quat.get_tuple(xyz=False))

        return string

    @classmethod
    def parse(cls, message):
        match = re.match(cls.message_regex, message)
        if match is not None:
            message = Bno055Message(float(match.group(1)), int(match.group(4)))
            message.packet_time = float(match.group(2))
            message.arduino_time = float(match.group(3))

            group_index = 5
            for index, vector in enumerate(message.vectors):
                elements = match.group(index + group_index).split(", ")
                for element_index, element in enumerate(elements):
                    vector[element_index] = float(element)

            return message
        else:
            return None


class BNO055(Arduino):
    def __init__(self, enabled=True):
        super(BNO055, self).__init__(
            "BNO055-IMU", enabled=enabled,
        )

    async def loop(self):
        arduino_start_time = self.start_time
        self.logger.info("initialization data: %s. Start time: %s" % (self.first_packet, arduino_start_time))
        counter = 0
        while self.device_active():
            while not self.empty():
                packet_time, packets = self.read()

                for packet in packets:
                    message = self.parse_packet(packet_time, packet, counter)
                    self.log_to_buffer(packet_time, message)
                    await self.broadcast(message)
                    counter += 1

            await asyncio.sleep(0.0)

    def parse_packet(self, packet_time, packet, packet_num):
        data = packet.split("\t")
        segment = ""
        message = Bno055Message(time.time(), packet_num)
        message.packet_time = packet_time
        try:
            for segment in data:
                if len(segment) > 0:
                    if segment[0] == "t":
                        message.arduino_time = float(segment[1:]) / 1000
                    elif segment[0] == "e":
                        message.euler[segment[1]] = math.radians(float(segment[2:]))
                    elif segment[0] == "a":
                        message.accel[segment[1]] = float(segment[2:])
                    elif segment[0] == "g":
                        message.gyro[segment[1]] = float(segment[2:])
                    elif segment[0] == "m":
                        message.mag[segment[1]] = float(segment[2:])
                    elif segment[0] == "l":
                        message.linaccel[segment[1]] = float(segment[2:])
                    elif segment[0] == "q":
                        message.quat[segment[1]] = float(segment[2:])
                    elif segment[0] == "s":
                        if segment[1] == "s":
                            message.system_status = int(segment[2:])
                        elif segment[1] == "a":
                            message.accel_status = int(segment[2:])
                        elif segment[1] == "g":
                            message.gyro_status = int(segment[2:])
                        elif segment[1] == "m":
                            message.mag_status = int(segment[2:])
                    else:
                        self.logger.warning("Invalid segment type! Segment: '%s', packet: '%s'" % (segment[0], data))
                else:
                    self.logger.warning("Empty segment! Packet: '%s'" % data)
        except ValueError:
            self.logger.error("Failed to parse: '%s'" % segment)

        return message


class ConsumerNode(Node):
    def __init__(self, enabled=True):
        super(ConsumerNode, self).__init__(enabled)

        self.producer_tag = "producer"
        self.producer_sub = self.define_subscription(self.producer_tag, required_attributes=("start_time",))
        self.producer_queue = None
        self.producer = None

        self.avg_time_sum = 0
        self.avg_packet_time_sum = 0
        self.avg_arduino_time_sum = 0
        self.avg_count = 0

    def take(self):
        self.producer_queue = self.producer_sub.get_queue()
        self.producer = self.producer_sub.get_producer()

        self.logger.info("Got producer named '%s'" % self.producer.name)

    async def loop(self):
        arduino_start_time = self.producer.start_time
        while True:
            message = await self.producer_queue.get()
            consumer_time = time.time()
            delta_t = consumer_time - arduino_start_time

            self.avg_time_sum += consumer_time - message.timestamp
            self.avg_packet_time_sum += consumer_time - message.packet_time
            self.avg_arduino_time_sum += message.arduino_time - delta_t
            self.avg_count += 1

    async def teardown(self):
        self.logger.info("average process delay: %s" % (self.avg_time_sum / self.avg_count))
        self.logger.info("average packet delay: %s" % (self.avg_packet_time_sum / self.avg_count))
        self.logger.info("average arduino delay: %s" % (self.avg_arduino_time_sum / self.avg_count))


class MyOrchestrator(Orchestrator):
    def __init__(self, event_loop):
        self.set_default(write=True, file_name="bno055_demo.log",
                         directory=os.path.join("logs", "bno055_demo", "%(name)s"))
        super(MyOrchestrator, self).__init__(event_loop)

        bno055 = BNO055()
        consumer = ConsumerNode()

        self.add_nodes(bno055, consumer)
        self.subscribe(bno055, consumer, consumer.producer_tag)


if __name__ == '__main__':
    run(MyOrchestrator)
