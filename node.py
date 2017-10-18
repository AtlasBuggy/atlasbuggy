import asyncio

from subscription import Subscription
from log.factory import make_logger
from log.default import default_settings


class Node:
    def __init__(self, enabled=True, logger=None):
        self.enabled = enabled
        self.name = self.__class__.__name__
        if logger is None:
            self.logger = make_logger(self.name, default_settings)
        else:
            self.logger = logger

        self.producer_subs = []
        self.consumer_subs = []

    def make_logger(self, *args, **kwargs):
        return make_logger(self.__class__.__name__, default_settings, *args, **kwargs)

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

    def _find_matching_subscription(self, message, service):
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
                return subscription, message

    @asyncio.coroutine
    def broadcast(self, message, service="default"):
        matched_subscription, message = self._find_matching_subscription(message, service)

        if matched_subscription is None:
            yield from asyncio.sleep(0.0)
        else:
            yield from matched_subscription.queue.put(message)

    def broadcast_nowait(self, message, service="default"):
        matched_subscription, message = self._find_matching_subscription(message, service)
        if matched_subscription is not None:
            if matched_subscription.error_on_full_queue:
                matched_subscription.queue.put_nowait(message)
            else:
                try:
                    matched_subscription.queue.put_nowait(message)
                except asyncio.QueueFull:
                    self.logger.info("queue full")

    def define_subscription(self, service="default", message_type=None, producer_type=None,
                            queue_size=None, error_on_full_queue=False):
        subscription = Subscription(service, message_type, producer_type, queue_size, error_on_full_queue)
        self.producer_subs.append(subscription)
        return subscription

    def append_subscription(self, subscription):
        self.consumer_subs.append(subscription)

    def __str__(self):
        return self.name
