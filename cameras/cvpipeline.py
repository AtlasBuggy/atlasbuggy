from atlasbuggy import ThreadedStream
from atlasbuggy.subscriptions import Update


class CvPipeline(ThreadedStream):
    def __init__(self, enabled, log_level, name=None, ):
        super(CvPipeline, self).__init__(enabled, name, log_level)

        self.capture = None
        self.capture_feed = None
        self.capture_tag = "capture"
        self.require_subscription(self.capture_tag, Update)

    def take(self, subscriptions):
        self.capture = self.subscriptions[self.capture_tag].stream
        self.capture_feed = self.subscriptions[self.capture_tag].queue

    def run(self):
        while self.running():
            while not self.capture_feed.empty():
                self.update_pipeline(self.capture_feed.get())

    def update_pipeline(self, frame):
        self.post(self.pipeline(frame))

    def post_behavior(self, data):
        if type(data) != tuple:
            return data.copy()
        else:
            return data[0].copy(), data[1:]

    def pipeline(self, frame):
        raise NotImplementedError("Please override this method.")
