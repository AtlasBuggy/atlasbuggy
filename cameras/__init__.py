import os
import cv2
import time
import numpy as np
from atlasbuggy.datastream import DataStream, ThreadedStream
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

    def take(self):
        self.recorder = self.streams["recorder"]

    def log_frame(self):
        self.logger.debug("frame #%s" % self.num_frames)

    def get_frame(self):
        with self.frame_lock:
            return self.frame

    def get_bytes_frame(self):
        with self.frame_lock:
            return self.bytes_frame

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


class VideoStream(DataStream):
    def __init__(self, file_name, directory, enabled, log_level):
        if file_name is None:
            file_name = time.strftime("%H;%M;%S.avi")
            if directory is None:
                # only use default if both directory and file_name are None.
                # Assume file_name has the full path if directory is None
                directory = time.strftime("videos/%Y_%b_%d")

        self.file_name = file_name
        self.directory = directory

        self.full_path = os.path.join(self.directory, self.file_name)
        super(VideoStream, self).__init__(
            enabled, file_name, log_level
        )

        self.capture = None
        self.is_recording = False

    def make_dirs(self):
        if not os.path.isdir(self.directory):
            os.makedirs(self.directory)

    def take(self):
        self.capture = self.streams["capture"]

    def start_recording(self):
        pass

    def record(self, frame):
        pass

    def stop_recording(self):
        pass
