import asyncio


class Subscription:
    def __init__(self, requested_service, expected_message_type, expected_producer_class, queue_size,
                 error_on_full_queue):
        self.requested_service = requested_service
        self.expected_message_type = expected_message_type
        self.expected_producer_class = expected_producer_class
        if queue_size is None:
            queue_size = 0
        self.queue_size = queue_size
        self.error_on_full_queue = error_on_full_queue

        self.producer_node = None
        self.consumer_node = None
        self.queue = None
        self.message_converter = None
        self.is_required = True

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
