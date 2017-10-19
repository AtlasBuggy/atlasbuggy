import asyncio
import logging

from subscription import Subscription
from log.factory import make_logger
from log.default import default_settings


class Node:
    def __init__(self, enabled=True, logger=None):
        self.enabled = enabled
        if logger is None:
            self.logger = make_logger(self.name, default_settings)
        else:
            self.logger = logger

        self.producer_subs = []
        self.consumer_subs = []
        self.services = {}

        self.event_loop = None  # assigned by the orchestrator when orchestrator.add_nodes is called

        self.log_buffer_start = "[log buffer start]\n"
        self.log_buffer_end = "[log buffer end]"
        self.log_buffer = self.log_buffer_start
        self.max_log_buf_size = 16384

    @property
    def name(self):
        return self.__class__.__name__

    def make_logger(self, *args, **kwargs):
        return make_logger(self.name, default_settings, *args, **kwargs)

    def log_to_buffer(self, level, timestamp, message):
        self.log_buffer += "[%s, %s]: %s\n" % (logging.getLevelName(level), timestamp, message)
        if len(self.log_buffer) > self.max_log_buf_size:
            self.dump_log_buffer()

    def dump_log_buffer(self):
        self.log_buffer += self.log_buffer_end
        self.logger.debug(self.log_buffer)
        self.log_buffer = self.log_buffer_start

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

    def _internal_teardown(self):
        self.dump_log_buffer()

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
                    self.logger.info(
                        "Producer '%s' is trying to put a message on consumer '%s's queue, but it is full" %
                        (matched_subscription.producer_node, matched_subscription.consumer_node))

    def define_subscription(self, tag, service="default", message_type=None, producer_type=None,
                            queue_size=None, error_on_full_queue=True):
        subscription = Subscription(tag, service, message_type, producer_type, queue_size, error_on_full_queue)
        self.producer_subs.append(subscription)
        return subscription

    def define_service(self, service="default", message_type=None):
        self.services[service] = message_type

    def append_subscription(self, subscription):
        self.consumer_subs.append(subscription)

    def __str__(self):
        return self.name
