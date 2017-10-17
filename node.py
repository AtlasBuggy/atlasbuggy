import asyncio
import logging

from subscription import Subscription
from log_factory import make_logger


class Node:
    def __init__(self, enabled=True, logger=None):
        self.enabled = enabled
        self.name = self.__class__.__name__
        if logger is None:
            self.logger = make_logger(self.name, logging.DEBUG)
        else:
            self.logger = logger

        self.producer_subs = []
        self.consumer_subs = []

    def make_logger(self, level=logging.INFO, write=True, log_format=None, file_name=None, directory=None,
                    custom_fields_fn=None):
        return make_logger(self.__class__.__name__, level, write, log_format, file_name, directory, custom_fields_fn)

    # ----- event order methods -----

    @asyncio.coroutine
    def setup(self):
        self.logger.info("setup")

    @asyncio.coroutine
    def loop(self):
        self.logger.info("loop")

    @asyncio.coroutine
    def teardown(self):
        self.logger.info("teardown")

    # ----- subscription methods -----

    def take(self):
        pass

    @asyncio.coroutine
    def broadcast(self, message, service="default"):
        broadcasted = False
        for subscription in self.consumer_subs:
            if subscription.expected_message_type is not None:
                if subscription.message_converter is not None:
                    message = subscription.message_converter(message)

                if not isinstance(message, subscription.expected_message_type):
                    raise ValueError(
                        "Consumer node '%s' expects message type '%s' from producer '%s'. Got type '%s'" % (
                            subscription.consumer_node, subscription.expected_message_type,
                            subscription.producer_node, type(message)))
            if subscription.requested_service == service:
                yield from subscription.queue.put(message)
                broadcasted = True

        if not broadcasted:
            yield from asyncio.sleep(0.0)

    def define_subscription(self, service="default", message_type=None, producer_type=None,
                            queue_size=None):
        subscription = Subscription(service, message_type, producer_type, queue_size)
        self.producer_subs.append(subscription)
        return subscription

    def append_subscription(self, subscription):
        self.consumer_subs.append(subscription)

    def __str__(self):
        return self.name
