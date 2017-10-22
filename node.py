import time
import asyncio
import logging

from .subscription import Subscription
from .log.factory import make_logger
from .log import default


class Node:
    def __init__(self, enabled=True, name=None, logger=None):
        self.enabled = enabled
        self._name = name
        if not self.is_logger_created():
            if logger is None:
                self.logger = make_logger(self.name, default.default_settings)
            else:
                self.logger = logger

        self.producer_subs = []
        self.consumer_subs = []
        self.subscription_tags = set()
        self.services = {}

        self.event_loop = None  # assigned by the orchestrator when orchestrator.add_nodes is called

        self.log_buffer = default.log_buffer_start
        self.max_log_buf_size = 16384

        self.start_time = time.time()

    @property
    def name(self):
        if not hasattr(self, "_name") or self._name is None:
            return self.__class__.__name__
        else:
            return self._name

    @name.setter
    def name(self, value):
        self._name = value

    def set_logger(self, *args, **kwargs):
        if self.is_logger_created():
            raise ValueError("A logger was created for this node already. Call this before the call to super().")
        self.logger = make_logger(self.name, default.default_settings, *args, **kwargs)

    def is_logger_created(self):
        return hasattr(self, "logger")

    def log_to_buffer(self, timestamp, message, level=logging.DEBUG):
        self.log_buffer += "[%s, %s]: %s\n" % (logging.getLevelName(level), timestamp, message)
        if len(self.log_buffer) > self.max_log_buf_size:
            self.dump_log_buffer()

    def dump_log_buffer(self):
        if len(self.log_buffer) > len(default.log_buffer_start):
            self.log_buffer += default.log_buffer_end
            self.logger.debug(self.log_buffer)

            self.logger.debug("logging message buffer (len=%s)" % len(self.log_buffer))

            self.log_buffer = default.log_buffer_start

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
        end_time = time.time()
        self.logger.info("Node took %ss to run" % (end_time - self.start_time))

    # ----- subscription methods -----

    def take(self):
        pass

    def producer_has_attributes(self, subscription, *attribute_names):
        producer = subscription.get_producer()
        for attribute_name in attribute_names:
            if not hasattr(producer, attribute_name):
                return False

        return True

    def producer_has_methods(self, subscription, *method_names):
        producer = subscription.get_producer()
        for method_name in method_names:
            if not hasattr(producer, method_name) or not callable(getattr(producer, method_name)):
                return False

        return True

    def _find_matching_subscriptions(self, message, service):
        results = []
        for subscription in self.consumer_subs:
            if not subscription.enabled:
                continue
            if subscription.expected_message_types is not None:
                if subscription.message_converter is not None:
                    message = subscription.message_converter(message)

                satisfied = False
                for expected_message_type in subscription.expected_message_types:
                    if isinstance(message, expected_message_type):
                        satisfied = True
                        break
                if not satisfied:
                    raise ValueError(
                        "Consumer node '%s' expects message type '%s' from producer '%s'. Got type '%s'" % (
                            subscription.consumer_node, subscription.expected_message_types,
                            subscription.producer_node, type(message)))
            if service == subscription.requested_service:
                results.append((subscription, message))
        return results

    @asyncio.coroutine
    def broadcast(self, message, service="default"):
        results = self._find_matching_subscriptions(message, service)

        if len(results) == 0:
            yield from asyncio.sleep(0.0)
        else:
            for matched_subscription, message in results:
                if matched_subscription.error_on_full_queue:
                    yield from matched_subscription.queue.put(message)
                else:
                    try:
                        yield from matched_subscription.queue.put(message)
                    except asyncio.QueueFull:
                        self.logger.info(
                            "Producer '%s' is trying to put a message on consumer '%s's queue, but it is full" % (
                                matched_subscription.producer_node, matched_subscription.consumer_node
                            )
                        )

    def broadcast_nowait(self, message, service="default"):
        results = self._find_matching_subscriptions(message, service)

        if len(results) != 0:
            for matched_subscription, message in results:
                if matched_subscription.error_on_full_queue:
                    matched_subscription.queue.put_nowait(message)
                else:
                    try:
                        matched_subscription.queue.put_nowait(message)
                    except asyncio.QueueFull:
                        self.logger.info(
                            "Producer '%s' is trying to put a message on consumer '%s's queue, but it is full" % (
                                matched_subscription.producer_node, matched_subscription.consumer_node
                            )
                        )

    def define_subscription(self, tag, service="default",
                            is_required=True,
                            message_type=None,
                            producer_type=None,
                            queue_size=None,
                            error_on_full_queue=False,
                            required_attributes=None,
                            required_methods=None):

        subscription = Subscription(tag, service, is_required, message_type, producer_type, queue_size, error_on_full_queue,
                                    required_attributes, required_methods)
        self.producer_subs.append(subscription)
        return subscription

    def is_subscribed(self, tag):
        return tag in self.subscription_tags

    def define_service(self, service="default", message_type=None):
        self.services[service] = message_type

    def append_subscription(self, subscription):
        self.consumer_subs.append(subscription)

    def __str__(self):
        return self.name
