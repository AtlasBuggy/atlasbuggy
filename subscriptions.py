from queue import Queue
from threading import Lock


class Subscription:
    def __init__(self, tag, stream, enabled=True):
        self.tag = tag
        self.stream = stream
        self.enabled = enabled
        self.description = "subscribing to"

    def post(self, data):
        pass


class Feed(Subscription):
    def __init__(self, tag, stream, enabled=True):
        super(Feed, self).__init__(tag, stream, enabled)
        self.queue = Queue()

        self.verb = "receiving feed from"

    def post(self, data):
        self.queue.put(data)


class Update(Subscription):
    def __init__(self, tag, stream, enabled=True):
        super(Update, self).__init__(tag, stream, enabled)
        self.mailbox = None
        self.box_lock = Lock()

        self.description = "receiving updates from"

    def post(self, data):
        with self.box_lock:
            self.mailbox = data
