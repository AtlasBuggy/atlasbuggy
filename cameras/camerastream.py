import os
import cv2
import time
import numpy as np
from atlasbuggy import ThreadedStream
from atlasbuggy.subscriptions import Feed
from threading import Lock

class CameraStream(ThreadedStream):
    def __init__(self, enabled, name, log_level):
        self.capture = None

        self.width = None
        self.height = None
        self.fps = None
        self.length_sec = 0.0
        self.fps_sum = 0.0
        self.fps_avg = 0.0
        self.prev_t = None

        self.frame = None
        self.bytes_frame = None
        self.num_frames = 0
        self.frame_lock = Lock()

        self.paused = False
        self.recorder = None

        super(CameraStream, self).__init__(enabled, name, log_level)

        self.recorder_tag = "recorder"

    def take(self, subscriptions):
        if self.recorder_tag in subscriptions:
            self.recorder = subscriptions[self.recorder_tag].stream

    def log_frame(self):
        self.logger.debug("frame #%s" % self.num_frames)

    def poll_for_fps(self):
        if self.prev_t is None:
            self.prev_t = time.time()
            return 0.0

        self.length_sec = time.time() - self.start_time
        self.fps_sum += 1 / (time.time() - self.prev_t)
        self.num_frames += 1
        self.fps_avg = self.fps_sum / self.num_frames
        self.prev_t = time.time()

    @staticmethod
    def bytes_to_numpy(frame):
        return cv2.imdecode(np.fromstring(frame, dtype=np.uint8), 1)

    @staticmethod
    def numpy_to_bytes(frame):
        return cv2.imencode(".jpg", frame)[1].tostring()
