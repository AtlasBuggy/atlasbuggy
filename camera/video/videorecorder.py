import os
import cv2
import time
import asyncio
from ... import get_platform
from ...datastream import AsyncStream
from ...subscriptions import Feed


class VideoRecorder(AsyncStream):
    def __init__(self, file_name=None, directory="", enabled=True, log_level=None,
                 width=None, height=None, fps=None):
        self.enabled = enabled

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
        self.opened = False
        self.required_buffer_len = 50

        self.set_path(file_name, directory)

        super(VideoRecorder, self).__init__(enabled, file_name, log_level)

        self.capture = None
        self.capture_feed = None
        self.capture_tag = "capture"
        self.require_subscription(self.capture_tag, Feed, required_attributes=("fps",))

    def take(self, subscriptions):
        self.capture = subscriptions[self.capture_tag].get_stream()
        self.capture_feed = subscriptions[self.capture_tag].get_feed()

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

    def start(self):
        self.make_dirs()

        if self.file_name.endswith('avi'):
            codec = 'MJPG'
        elif self.file_name.endswith('mp4'):
            if get_platform() == 'mac':
                codec = 'MP4V'
            else:
                # TODO: Figure out mp4 recording in linux
                # codec = 'DIVX'
                codec = 'MJPG'
                self.file_name = self.file_name[:-3] + "avi"
                self.full_path = os.path.join(self.file_name, self.directory)
        else:
            raise ValueError("Invalid file format")
        self.fourcc = cv2.VideoWriter_fourcc(*codec)
        self.video_writer = cv2.VideoWriter()

        self.is_recording = True

        # if not self.live_feed and self.width is not None and self.height is not None:
        #     self._dump_buffer()

    def record(self, frame):
        if self.opened:
            self._write(frame)
        else:
            if len(self.frame_buffer) >= self.required_buffer_len:
                self._dump_buffer()
                self.logger.debug("Dumping buffer. %s frames reached" % self.required_buffer_len)
            else:
                self.frame_buffer.append(frame)

    async def run(self):
        while self.is_running():
            while not self.capture_feed.empty():
                self.record(await self.capture_feed.get())
                self.capture_feed.task_done()
            await asyncio.sleep(0.5 / self.capture.fps)

    def poll_for_fps(self):
        if self.prev_t is None:
            self.prev_t = time.time()
            return 0.0

        self.length_sec = time.time() - self.start_time
        self.fps_sum += 1 / (time.time() - self.prev_t)
        self.num_frames += 1
        self.fps_avg = self.fps_sum / self.num_frames
        self.prev_t = time.time()

    def _dump_buffer(self):
        if not self.opened and len(self.frame_buffer) > 0:
            self.height, self.width = self.frame_buffer[0].shape[0:2]
            if self.fps is None:
                self.fps = self.capture.fps

            self.logger.debug(
                "Writing to '%s'. width = %s, height = %s, fps = %s" % (
                    self.full_path, self.width, self.height, self.fps)
            )
            self.video_writer.open(
                self.full_path, self.fourcc, self.fps, (self.width, self.height), True
            )
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
        self.logger.debug("Writing frame #%s" % self.num_frames)
        if len(frame.shape) == 2:
            self.video_writer.write(cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR))
        else:
            self.video_writer.write(frame)

    def stop(self):
        if self.is_recording:
            if not self.opened:  # if required frame buffer size hasn't been met...
                self._dump_buffer()
            self.video_writer.release()
            self.is_recording = False

    def make_dirs(self):
        if self.directory is not None and len(self.directory) > 0 and not os.path.isdir(self.directory):
            os.makedirs(self.directory)
