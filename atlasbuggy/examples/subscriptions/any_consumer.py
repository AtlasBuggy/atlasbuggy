import os
import time
import random
import asyncio
from atlasbuggy import Message, Node, Orchestrator, run


class ProducerMessage1(Message):
    num_args = 4

    def __init__(self, timestamp, n, w=0.0, x=0.0, y=0.0, z=0.0):
        self.timestamp = timestamp
        self.w = w
        self.x = x
        self.y = y
        self.z = z
        super(ProducerMessage1, self).__init__(timestamp, n)

        self.id = "%s-%s" % (self.name, n)

    def __str__(self):
        return "ProducerMessage1(t=%s, n=%s, w=%s, x=%s, y=%s, z=%s)" % (
            self.timestamp, self.n, self.w, self.x, self.y, self.z)


class ProducerMessage2(Message):
    num_args = 3

    def __init__(self, timestamp, n, x=0.0, y=0.0, z=0.0):
        self.timestamp = timestamp
        self.x = x
        self.y = y
        self.z = z
        super(ProducerMessage2, self).__init__(timestamp, n)

        self.id = "%s-%s" % (self.name, n)

    def __str__(self):
        return "ProducerMessage2(t=%s, n=%s, x=%s, y=%s, z=%s)" % (
            self.timestamp, self.n, self.x, self.y, self.z)


class ProducerMessage3(Message):
    num_args = 2

    def __init__(self, timestamp, n, x=0.0, y=0.0):
        self.timestamp = timestamp
        self.x = x
        self.y = y
        super(ProducerMessage3, self).__init__(timestamp, n)

        self.id = "%s-%s" % (self.name, n)

    def __str__(self):
        return "ProducerMessage3(t=%s, n=%s, x=%s, y=%s)" % (
            self.timestamp, self.n, self.x, self.y)


class ConsumerMessage(Message):
    def __init__(self, timestamp, message_id, n, a=0.0, b=0.0):
        self.timestamp = timestamp
        self.a = a
        self.b = b
        super(ConsumerMessage, self).__init__(timestamp, n)

        self.id = message_id

    def __str__(self):
        return "ConsumerMessage(t=%s, id=%s, n=%s a=%s, b=%s)" % (self.timestamp, self.id, self.n, self.a, self.b)


class GenericProducerBase(Node):
    def __init__(self, MessageType, enabled=True):
        super(GenericProducerBase, self).__init__(enabled)

        self.MessageType = MessageType

    async def loop(self):
        counter = 0
        while True:
            producer_time = time.time()
            args = [random.random() for _ in range(self.MessageType.num_args)]
            message = self.MessageType(
                producer_time, counter,
                *args
            )
            counter += 1
            await self.broadcast(message)

            await asyncio.sleep(0.5)
            self.logger.info("sending: %s" % message)


class GenericProducer1(GenericProducerBase):
    def __init__(self, enabled=True):
        super(GenericProducer1, self).__init__(ProducerMessage1, enabled)


class GenericProducer2(GenericProducerBase):
    def __init__(self, enabled=True):
        super(GenericProducer2, self).__init__(ProducerMessage2, enabled)


class GenericProducer3(GenericProducerBase):
    def __init__(self, enabled=True):
        super(GenericProducer3, self).__init__(ProducerMessage3, enabled)


class AnyConsumer(Node):
    def __init__(self, enabled=True):
        super(AnyConsumer, self).__init__(enabled)

        self.any_tag = "any"
        self.any_sub = self.define_subscription(self.any_tag, message_type=ConsumerMessage)
        self.any_queue = None

    def take(self):
        self.any_queue = self.any_sub.get_queue()

    async def loop(self):
        while True:
            while not self.any_queue.empty():
                message = await self.any_queue.get()
                consumer_time = time.time()

                self.logger.info("time diff: %s" % (consumer_time - message.timestamp))
                self.logger.info("receiving: %s" % message)

            await asyncio.sleep(0.5)


def producer1_to_consumer(message: ProducerMessage1):
    return ConsumerMessage(message.timestamp, message.id, message.n, message.w + message.x, message.y + message.z)


def producer2_to_consumer(message: ProducerMessage2):
    return ConsumerMessage(message.timestamp, message.id, message.n, message.x, message.y + message.z)


def producer3_to_consumer(message: ProducerMessage3):
    return ConsumerMessage(message.timestamp, message.id, message.n, message.x, message.y)


class MyOrchestrator(Orchestrator):
    def __init__(self, event_loop):
        super(MyOrchestrator, self).__init__(event_loop)

        generic_producer1 = GenericProducer1()
        generic_producer2 = GenericProducer2()
        generic_producer3 = GenericProducer3()
        any_consumer = AnyConsumer()

        self.add_nodes(generic_producer1, generic_producer2, generic_producer3, any_consumer)

        self.subscribe(generic_producer1, any_consumer, any_consumer.any_tag, message_converter=producer1_to_consumer)
        self.subscribe(generic_producer2, any_consumer, any_consumer.any_tag, message_converter=producer2_to_consumer)
        self.subscribe(generic_producer3, any_consumer, any_consumer.any_tag, message_converter=producer3_to_consumer)


if __name__ == '__main__':
    run(MyOrchestrator)
