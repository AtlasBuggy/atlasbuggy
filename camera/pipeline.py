import time
from atlasbuggy import ThreadedStream
from atlasbuggy.subscriptions import Update


class Pipeline(ThreadedStream):
    def __init__(self, enabled, log_level, name=None):
        super(Pipeline, self).__init__(enabled, name, log_level)
        self.width = None
        self.height = None

        self.fps_sum = 0.0
        self.fps = 30.0
        self.prev_t = None
        self.current_frame_num = 0
        self.num_frames = None
        self.length_sec = 0.0
        self.frame = None
        self.paused = False

        self.capture = None
        self.capture_feed = None
        self.capture_tag = "capture"
        self.require_subscription(self.capture_tag, Update,
                                  required_attributes=("width", "height", "num_frames"))

    def take(self, subscriptions):
        self.capture = self.subscriptions[self.capture_tag].get_stream()
        self.capture_feed = self.subscriptions[self.capture_tag].get_feed()

        self.width = self.capture.width
        self.height = self.capture.height
        self.num_frames = self.capture.num_frames

    def set_pause(self, state):
        self.capture_feed.enabled = not state
        self.paused = state

    def run(self):
        while self.is_running():
            if self.prev_t is None:
                self.prev_t = time.time()
            self.length_sec = self.dt()
            prev_num = self.current_frame_num

            while not self.capture_feed.empty():
                self.current_frame_num += 1
                self.frame = self.pipeline(self.capture_feed.get())
                self.post(self.frame)

            if self.current_frame_num != prev_num:
                delta_num = self.current_frame_num - prev_num
                self.fps_sum += delta_num / (time.time() - self.prev_t)
                self.fps = self.fps_sum / self.current_frame_num
                self.prev_t = time.time()

    def default_post_service(self, data):
        return data.copy()

    def pipeline(self, frame):
        raise NotImplementedError("Please override this method.")
