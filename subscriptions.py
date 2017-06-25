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

    def get(self):
        pass


class Feed(Subscription):
    def __init__(self, tag, stream, enabled=True):
        super(Feed, self).__init__(tag, stream, enabled)
        self.queue = Queue()

        self.description = "receiving feed from"

    def post(self, data):
        self.queue.put(data)

    def get(self):
        return self.queue.get()


class Update(Subscription):
    def __init__(self, tag, stream, enabled=True):
        super(Update, self).__init__(tag, stream, enabled)
        self.queue = _SingletonQueue()
        self.description = "receiving updates from"

    def post(self, data):
        self.queue.put(data)

    def get(self):
        return self.queue.get()


class _SingletonQueue:
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
