from queue import Queue
from atlasbuggy.datastream import ThreadedStream


class CvPipeline(ThreadedStream):
    def __init__(self, enabled, log_level, name=None, post_bytes=False, use_output_queue=False):
        super(CvPipeline, self).__init__(enabled, name, log_level)

        self.capture = None
        self.post_bytes = post_bytes
        self.capture_feed = None

    def take(self):
        self.capture = self.streams["capture"]

    def start(self):
        self.capture_feed = self.get_feed(self.capture)

    def run(self):
        while self.running():
            if self.capture.post_frames:

                while not self.capture_feed.empty():
                    output = self.capture_feed.get()
                    while self.capture_feed.qsize() > 5:
                        output = self.capture_feed.get()
                    if self.capture.post_bytes:
                        frame, bytes_frame = output
                    else:
                        frame = output[0]
                    self.update_pipeline(frame)

    def update_pipeline(self, frame):
        output = self.pipeline(frame)
        if type(output) != tuple:
            frame = output
        else:
            frame = output[0]

        if self.post_bytes:
            bytes_frame = self.capture.numpy_to_bytes(frame)
        else:
            bytes_frame = None

        self.post_all((frame, bytes_frame))

    def post_single(self, feed, data):
        frame, bytes_frame = data
        if bytes_frame is not None:
            feed.put((frame.copy(), bytes_frame))
        else:
            feed.put(frame.copy())

    def pipeline(self, frame):
        raise NotImplementedError("Please override this method.")
