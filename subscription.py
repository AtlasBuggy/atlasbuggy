import asyncio


def wrap_iter(iterable):
    if iterable is not None:
        try:
            iter(iterable)
        except TypeError:
            iterable = (iterable,)

    return iterable


class Subscription:
    def __init__(self, tag, requested_service, is_required, expected_message_types, expected_producer_classes, queue_size,
                 error_on_full_queue, required_attributes, required_methods):
        self.tag = tag
        self.enabled = True
        self.requested_service = requested_service
        self.expected_message_types = expected_message_types
        self.expected_producer_classes = expected_producer_classes
        if queue_size is None:
            queue_size = 0
        self.queue_size = queue_size
        self.error_on_full_queue = error_on_full_queue
        self.required_attributes = required_attributes
        self.required_methods = required_methods

        self.producer_node = None
        self.consumer_node = None
        self.queue = None
        self.message_converter = None
        self.is_required = is_required

        self.expected_message_types = wrap_iter(self.expected_message_types)
        self.expected_producer_classes = wrap_iter(self.expected_producer_classes)

    def check_subscription(self):
        if self.is_required:
            if self.producer_node is None or self.consumer_node is None:
                raise ValueError("Subscription not applied!! Please call subscribe() in your orchestrator class")

    def set_event_loop(self, event_loop):
        self.queue = asyncio.Queue(self.queue_size, loop=event_loop)

    @asyncio.coroutine
    def broadcast(self, message):
        yield from self.queue.put(message)

    def get_queue(self):
        self.check_subscription()
        return self.queue

    def get_producer(self):
        self.check_subscription()
        return self.producer_node
