from queue import Queue
from threading import Lock
from atlasbuggy.datastream import ThreadedStream


class CvPipeline(ThreadedStream):
    def __init__(self, enabled, log_level, name=None, generate_bytes=False, use_output_queue=False):
        super(CvPipeline, self).__init__(enabled, name, log_level)
        self.capture = None

        self.frame = None
        self.bytes_frame = None
        self.frame_lock = Lock()

        self.generate_bytes = generate_bytes
        self.output_queue = Queue()
        self.use_output_queue = use_output_queue

    def take(self):
        self.capture = self.streams["capture"]

    def run(self):
        if self.capture is not None:
            while self.running():
                if self.capture.frame is not None:
                    self.update_pipeline(self.capture.get_frame())
                else:
                    self.bytes_frame = None
                    self.frame = None

    def get(self):
        while not self.output_queue.empty():
            yield self.output_queue.get()

    def update_pipeline(self, frame):
        output = self.pipeline(frame)
        if type(output) != tuple:
            self.frame = output
        else:
            self.frame = output[0]
            if self.use_output_queue:
                self.output_queue.put(output[1:])

        if self.generate_bytes:
            self.bytes_frame = self.capture.numpy_to_bytes(self.frame)

    def pipeline(self, frame):
        raise NotImplementedError("Please override this method.")
