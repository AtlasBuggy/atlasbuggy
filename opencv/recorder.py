import os
import cv2
import time
import asyncio

from atlasbuggy import Node

from .messages import ImageMessage


class OpenCVRecorder(Node):
    def __init__(self, file_name=None, directory="", enabled=True, logger=None, width=None, height=None, fps=None):
        file_name_only = os.path.split(file_name)[-1]  # remove directories that might be in the name
        file_name_only = os.path.splitext(file_name_only)[0]  # remove extensions
        name = self.name + "-" + file_name_only
        super(OpenCVRecorder, self).__init__(enabled, name, logger)

        self.is_recording = False
        self.fps = fps
        self.num_frames = 0
        self.length_sec = 0.0

        self.fps_sum = 0.0
        self.fps_avg = 30.0
        self.prev_t = None

        self.width = width
        self.height = height
        self.video_writer = None
        self.fourcc = None

        self.frame_buffer = []
        self.buffer_size = 25
        self.opened = False

        self.set_path(file_name, directory)

        self.capture = None
        self.capture_queue = None
        self.capture_tag = "capture"
        self.capture_sub = self.define_subscription(self.capture_tag, message_type=ImageMessage,
                                                    required_attributes=("fps",))

    def set_path(self, file_name=None, directory=None):
        if file_name is None:
            file_name = time.strftime("%H_%M_%S.avi")
            if directory is None:
                # only use default if both directory and file_name are None.
                # Assume file_name has the full path if directory is None
                directory = time.strftime("videos/%Y_%b_%d")

        self.file_name = file_name
        self.directory = directory

        ext_index = self.file_name.rfind(".")
        if ext_index == -1:
            raise ValueError("An extension is required: %s" % self.file_name)

        self.full_path = os.path.join(self.directory, self.file_name)

    def take(self):
        self.capture = self.capture_sub.get_producer()
        self.capture_queue = self.capture_sub.get_queue()

    def make_dirs(self):
        if self.directory is not None and len(self.directory) > 0 and not os.path.isdir(self.directory):
            os.makedirs(self.directory)

    @asyncio.coroutine
    def setup(self):
        self.make_dirs()

        codec = 'MJPG'
        self.fourcc = cv2.VideoWriter_fourcc(*codec)
        self.video_writer = cv2.VideoWriter()

        self.is_recording = True

    def record(self, frame):
        if self.opened:
            self._write(frame)
        else:
            if len(self.frame_buffer) >= self.buffer_size:
                self._dump_buffer()
                self.logger.debug("Dumping buffer. %s frames reached" % self.buffer_size)
            else:
                self.frame_buffer.append(frame)

    def _dump_buffer(self):
        self.logger.info("dumping frame buffer. Size: %s" % len(self.frame_buffer))
        if not self.opened and len(self.frame_buffer) > 0:
            self.height, self.width = self.frame_buffer[0].shape[0:2]
            if self.fps is None:
                self.fps = self.capture.fps

            self.logger.info(
                "Writing to '%s'. width = %s, height = %s, fps = %s" % (
                    self.full_path, self.width, self.height, self.fps)
            )
            self.video_writer.open(
                self.full_path, self.fourcc, self.fps, (self.width, self.height), True
            )
            self.logger.info("Writing %s frames" % len(self.frame_buffer))

            while len(self.frame_buffer) > 0:
                self._write(self.frame_buffer.pop(0))
            self.opened = True
        else:
            message = ""
            if self.opened:
                message += "Video writer was already opened. "
            if len(self.frame_buffer) == 0:
                message += "Frame buffer has no frames. "
            self.logger.debug("Not dumping. " + message)

    def _write(self, frame):
        if self.height is None:
            self.height = frame.shape[0]
        if self.width is None:
            self.width = frame.shape[1]

        if frame.shape[0:2] != (self.height, self.width):
            frame = cv2.resize(frame, (self.height, self.width))

        self.num_frames += 1
        if len(frame.shape) == 2:  # frames must have 3 channels
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        self.video_writer.write(frame)

    def poll_for_fps(self):
        if self.prev_t is None:
            self.prev_t = time.time()
            return 0.0

        self.length_sec = time.time() - self.start_time
        self.fps_sum += 1 / (time.time() - self.prev_t)
        self.num_frames += 1
        self.fps_avg = self.fps_sum / self.num_frames
        self.prev_t = time.time()

    @asyncio.coroutine
    def loop(self):
        while True:
            while not self.capture_queue.empty():
                message = yield from self.capture_queue.get()
                self.logger.info("Recording frame #%s. Delay: %s" % (message.n, time.time() - message.timestamp))
                self.record(message.image)
                self.poll_for_fps()

            yield from asyncio.sleep(0.5 / self.capture.fps)  # operate faster than the camera

    @asyncio.coroutine
    def teardown(self):
        if self.is_recording:
            if not self.opened:  # if required frame buffer size hasn't been met, dump the buffer
                self._dump_buffer()
            self.video_writer.release()
            self.is_recording = False
