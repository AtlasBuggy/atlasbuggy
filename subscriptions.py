import asyncio
from .janus import Queue
from threading import Lock


class Subscription:
    """
    Base class for defining the relationship between streams. For this subscription type, the subscriber gets an
    instance of the other stream. Subscription classes are shared between a channel and a subscriber.
     
    A subscriber stream (or just subscriber) is a stream that is subscribed to another stream.
    A channel stream (or just channel) is a stream that posts content to its subscribers if it has any.
    """

    def __init__(self, tag, producer_stream, service="default", enabled=True):
        """
        :param tag: Name that this subscription will be under 
        :param producer_stream: An instance of DataStream
        :param service: service tag this subscription is requesting
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

    def set_consumer(self, consumer_stream):
        """
        The data stream requesting the subscription will supply a reference to itself. For internal use.
         
        :param consumer_stream: Subclass of DataStream
        """
        self.consumer_stream = consumer_stream

    def get_stream(self):
        """
        Get an instance of the producer stream.
        
        :return: Subclass of DataStream 
        """
        return self.producer_stream

    def get_feed(self):
        """
        Get an instance of the subscription feed if the subscription has one.
        ValueError is raised if there is no feed.
        
        :return: An instance of the subscription feed 
        """
        raise ValueError("Subscriptions of type '%s' don't supply feeds" % self.__class__.__name__)

    @asyncio.coroutine
    def async_post(self, data):
        """
        Behavior for posting to a feed based subscription asynchronously
        :param data: Data to post to subscribers. When posting lists, make sure to copy them if you intend to modify
            its contents in the subscriber's stream
        """
        yield from asyncio.sleep(0.0)

    def sync_post(self, data):
        """
        Behavior for posting to a feed based subscription on a thread
        :param data: Data to post to subscribers. When posting lists, make sure to copy them if you intend to modify
            its contents in the subscriber's stream
        """
        pass

    def __repr__(self):
        return "%s(tag='%s', producer_stream=%s, consumer_stream=%s)" % (
            self.__class__.__name__, self.tag, self.producer_stream, self.consumer_stream)


class Feed(Subscription):
    """
    This subscription type is a queue. Any data posted gets queued up in the feed
    """

    def __init__(self, tag, producer_stream, service="default", enabled=True):
        """
        :param tag: Name that this subscription will be under 
        :param producer_stream: An instance of DataStream
        :param service: service tag this subscription is requesting
        :param enabled: Disable or enable this subscription
        """
        super(Feed, self).__init__(tag, producer_stream, service, enabled)
        self.queue = None
        self.description = "receiving feed from"  # for debug printing

    def set_consumer(self, consumer_stream):
        """
        The data stream requesting the subscription will supply a reference to itself. For internal use.

        :param consumer_stream: Subclass of DataStream
        """
        self.consumer_stream = consumer_stream
        self.queue = Queue(loop=consumer_stream.asyncio_loop)

    def get_feed(self):
        """
        Get an instance of the subscription feed if the subscription has one.
        ValueError is raised if there is no feed.
        
        :return: An instance of the subscription feed 
        """
        if self.is_async:
            return self.queue.async_q
        else:
            return self.queue.sync_q

    @asyncio.coroutine
    def async_post(self, data, **kwargs):
        """
        Behavior for posting to a feed based subscription asynchronously
        :param data: Data to post to subscribers. When posting lists, make sure to copy them if you intend to modify
            its contents in the subscriber's stream
        """
        yield from self.queue.async_q.put(data)

    def sync_post(self, data, **kwargs):
        """
        Behavior for posting to a feed based subscription on a thread
        :param data: Data to post to subscribers. When posting lists, make sure to copy them if you intend to modify
            its contents in the subscriber's stream
        """
        self.queue.sync_q.put(data, **kwargs)


class Update(Subscription):
    """
    This subscription type is like a mailbox. The subscriber gets the latest data and only the latest data
    """

    def __init__(self, tag, producer_stream, service="default", enabled=True):
        """
        :param tag: Name that this subscription will be under 
        :param producer_stream: An instance of DataStream
        :param service: service tag this subscription is requesting
        :param enabled: Disable or enable this subscription
        """
        super(Update, self).__init__(tag, producer_stream, service, enabled)
        self.mailbox = _SingletonQueue()
        self.description = "receiving updates from"  # for debug printing

    def get_feed(self):
        """
        Get an instance of the subscription feed if the subscription has one.
        ValueError is raised if there is no feed.

        :return: An instance of the subscription feed 
        """
        return self.mailbox

    @asyncio.coroutine
    def async_post(self, data):
        """
        Behavior for posting to an update based subscription
        :param data: Data to post to subscribers. When posting lists, make sure to copy them if you intend to modify
            its contents in the subscriber's stream
        """
        self.mailbox.put(data)
        yield from asyncio.sleep(0.0)

    def sync_post(self, data):
        """
        Behavior for posting to a feed based subscription on a thread
        :param data: Data to post to subscribers. When posting lists, make sure to copy them if you intend to modify
            its contents in the subscriber's stream
        """
        self.mailbox.put(data)


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
