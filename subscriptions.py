from queue import Queue
from threading import Lock


class Subscription:
    """
    Base class for defining the relationship between streams. For this subscription type, the subscriber gets an
    instance of the other stream. Subscription classes are shared between a channel and a subscriber
     
    A subscriber stream (or just subscriber) is a stream that is subscribed to another stream.
    A channel stream (or just channel) is a stream that posts content to its subscribers if it has any
    """
    def __init__(self, tag, stream, callback=None, enabled=True):
        """
        :param tag: Name that this subscription will be under 
        :param stream: An instance of DataStream
        :param callback: when the channel posts, use this optional function handle to add some behavior
            (not recommended since this method will be run on the channel's thread which can get messy)
        :param enabled: Disable or enable this subscription
        """
        self.tag = tag
        self.stream = stream
        self.enabled = enabled
        self.description = "subscribing to"  # for debug printing
        self.callback = callback

    def post(self, data):
        """
        Base behavior for posting to subscribers. No action by default.
        :param data: Data to post to subscribers. When posting lists, make sure to copy them if you intend to modify
            its contents in the subscriber's stream
        """
        pass

    def get(self):
        """
        Base behavior for getting data from a channel. No action by default
        :return: Any data that was posted
        """
        pass


class Feed(Subscription):
    """
    This subscription type is a queue. Any data posted gets queued up in the feed
    """
    def __init__(self, tag, stream, callback=None, enabled=True):
        super(Feed, self).__init__(tag, stream, callback, enabled)
        self.queue = Queue()

        self.description = "receiving feed from"  # for debug printing

    def post(self, data):
        """
        Behavior for posting to a feed based subscription
        :param data: Data to post to subscribers. When posting lists, make sure to copy them if you intend to modify
            its contents in the subscriber's stream
        """
        self.queue.put(data)

    def get(self):
        """
        Get from the queue (blocking operation if nothing is present)
        :return: newest item from the queue
        """
        return self.queue.get()


class Update(Subscription):
    """
    This subscription type is like a mailbox. The subscriber gets the latest data and only the latest data
    """
    def __init__(self, tag, stream, callback=None, enabled=True):
        super(Update, self).__init__(tag, stream, callback, enabled)
        self.queue = _SingletonQueue()
        self.description = "receiving updates from"  # for debug printing

    def post(self, data):
        """
        Behavior for posting to an update based subscription
        :param data: Data to post to subscribers. When posting lists, make sure to copy them if you intend to modify
            its contents in the subscriber's stream
        """
        self.queue.put(data)

    def get(self):
        """
        Get from the mailbox
        :return: newest item from the mailbox
        """
        return self.queue.get()


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
