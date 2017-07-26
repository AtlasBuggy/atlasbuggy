import asyncio
from .janus import Queue
from threading import Lock


class Subscription:
    """
    Base class for defining the relationship between streams. For this subscription type, the subscriber gets an
    instance of the other stream. Subscription classes are shared between a channel and a subscriber
     
    A subscriber stream (or just subscriber) is a stream that is subscribed to another stream.
    A channel stream (or just channel) is a stream that posts content to its subscribers if it has any
    """

    def __init__(self, tag, producer_stream, service="default", enabled=True):
        """
        :param tag: Name that this subscription will be under 
        :param producer_stream: An instance of DataStream
        :param enabled: Disable or enable this subscription
        """
        assert type(tag) == str, "tag must be a string: %s" % tag
        self.tag = tag
        self.producer_stream = producer_stream
        self.enabled = enabled
        self.consumer_stream = None
        self.service = service
        self.description = "subscribing to"  # for debug printing
        self.is_async = False

    def set_consumer(self, subscriber):
        self.consumer_stream = subscriber

    def get_stream(self):
        return self.producer_stream

    def get_feed(self):
        return None

    async def async_post(self, data):
        """
        Behavior for posting to a feed based subscription
        :param data: Data to post to subscribers. When posting lists, make sure to copy them if you intend to modify
            its contents in the subscriber's stream
        """
        await asyncio.sleep(0.0)

    def sync_post(self, data):
        pass

    def __repr__(self):
        return "%s(tag='%s', producer_stream=%s, consumer_stream=%s)" % (
            self.__class__.__name__, self.tag, self.producer_stream, self.consumer_stream)


class Feed(Subscription):
    """
    This subscription type is a queue. Any data posted gets queued up in the feed
    """

    def __init__(self, tag, producer_stream, service="default", enabled=True):
        super(Feed, self).__init__(tag, producer_stream, service, enabled)
        self.queue = None
        self.description = "receiving feed from"  # for debug printing

    def set_consumer(self, consumer_stream):
        self.consumer_stream = consumer_stream
        self.queue = Queue(loop=consumer_stream.asyncio_loop)

    def get_feed(self):
        if self.is_async:
            return self.queue.async_q
        else:
            return self.queue.sync_q

    async def async_post(self, data):
        await self.queue.async_q.put(data)

    def sync_post(self, data):
        self.queue.sync_q.put(data)


class Update(Subscription):
    """
    This subscription type is like a mailbox. The subscriber gets the latest data and only the latest data
    """

    def __init__(self, tag, producer_stream, service="default", enabled=True):
        super(Update, self).__init__(tag, producer_stream, service, enabled)
        self.mailbox = _SingletonQueue()
        self.description = "receiving updates from"  # for debug printing

    async def async_post(self, data):
        """
        Behavior for posting to an update based subscription
        :param data: Data to post to subscribers. When posting lists, make sure to copy them if you intend to modify
            its contents in the subscriber's stream
        """
        self.mailbox.put(data)
        await asyncio.sleep(0.0)

    def sync_post(self, data):
        self.mailbox.put(data)

    def get_feed(self):
        return self.mailbox


class Callback(Subscription):
    def __init__(self, tag, producer_stream, service="default", enabled=True):
        super(Callback, self).__init__(tag, producer_stream, service, enabled)
        self.callback_fn = None

    def set_callback(self, callback_fn):
        self.callback_fn = callback_fn
        assert callable(self.callback_fn)

    async def async_post(self, data):
        await self.callback_fn(data)

    def sync_post(self, data):
        self.callback_fn(data)


class _SingletonQueue:
    """
    A queue that has a size of one. This acts a supplement to the Update class
    """

    def __init__(self):
        self.queue = [None]
        self.lock = Lock()

    def empty(self):
        return self.queue[0] is None

    def put(self, data):
        with self.lock:
            self.queue[0] = data

    def get(self):
        data = self.queue[0]
        self.queue[0] = None
        return data
