import time
from ..datastream import ThreadedStream
from ..subscriptions import Update


class Pipeline(ThreadedStream):
    def __init__(self, enabled, log_level, name=None):
        super(Pipeline, self).__init__(enabled, log_level, name)
        self.width = None
        self.height = None

        self.fps_sum = 0.0
        self.fps = 30.0
        self.prev_t = None
        self.num_frames = None
        self.length_sec = 0.0
        self.frame = None
        self.paused = False
        self.processed_frame_counter = 0

        self.capture = None
        self.capture_feed = None
        self.capture_tag = "capture"
        self.require_subscription(self.capture_tag, Update,
                                  required_attributes=("width", "height", "num_frames", "current_frame_num", "set_pause"))

    def take(self, subscriptions):
        self.capture = self.subscriptions[self.capture_tag].get_stream()
        self.capture_feed = self.subscriptions[self.capture_tag].get_feed()

        self.width = self.capture.width
        self.height = self.capture.height
        self.num_frames = self.capture.num_frames

        self.take_from_pipeline(subscriptions)

    def take_from_pipeline(self, subscriptions):
        pass

    def set_pause(self, state):
        self.capture_feed.enabled = not state
        self.capture.set_pause(state)
        self.paused = state

    def get_pause(self):
        return self.paused

    def set_frame(self, position):
        self.capture.set_frame(position)

    @property
    def current_frame_num(self):
        if self.capture is not None:
            return self.capture.current_frame_num
        else:
            return 0

    def run(self):
        while self.is_running():
            if self.prev_t is None:
                self.prev_t = time.time()
            self.length_sec = self.dt()
            prev_num = self.processed_frame_counter

            while not self.capture_feed.empty():
                self.processed_frame_counter += 1
                self.frame = self.pipeline(self.capture_feed.get())
                self.post(self.frame)

            if self.processed_frame_counter != prev_num:
                delta_num = self.processed_frame_counter - prev_num
                self.fps_sum += delta_num / (time.time() - self.prev_t)
                self.fps = self.fps_sum / self.processed_frame_counter
                self.prev_t = time.time()

    def default_post_service(self, data):
        return data.copy()

    def pipeline(self, frame):
        raise NotImplementedError("Please override this method.")
