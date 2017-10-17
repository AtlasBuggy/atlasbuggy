import asyncio


class Subscription:
    def __init__(self, requested_service, expected_message_type, expected_producer_class, queue_size):
        self.producer_node = None
        self.consumer_node = None

        self.requested_service = requested_service
        self.expected_message_type = expected_message_type
        self.expected_producer_class = expected_producer_class
        if queue_size is None:
            queue_size = 0
        self.queue_size = queue_size
        self.queue = None

    def set_event_loop(self, event_loop):
        self.queue = asyncio.Queue(self.queue_size, loop=event_loop)

    @asyncio.coroutine
    def broadcast(self, message):
        yield from self.queue.put(message)

    def get_queue(self):
        return self.queue

    def get_producer(self):
        return self.producer_node
