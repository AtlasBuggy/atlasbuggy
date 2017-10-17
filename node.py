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
        # broadcasted = False
        for subscription in self.consumer_subs:
            if subscription.expected_message_type is None or isinstance(message, subscription.expected_message_type):
                if subscription.requested_service == service:
                    yield from subscription.queue.put(message)
                    # broadcasted = True

        # if not broadcasted:
        #     yield from asyncio.sleep(0.0)

    def define_subscription(self, requested_service="default", expected_message_type=None, expected_producer_class=None,
                            queue_size=None):
        subscription = Subscription(requested_service, expected_message_type, expected_producer_class, queue_size)
        self.producer_subs.append(subscription)
        return subscription

    def append_subscription(self, subscription):
        self.consumer_subs.append(subscription)
