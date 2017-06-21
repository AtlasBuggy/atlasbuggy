import os
import cv2
import time
import asyncio
from threading import Lock
# from atlasbuggy.datastream import AsyncStream
from atlasbuggy.cameras import CameraStream
from atlasbuggy.serial.clock import Clock


class VideoPlayer(CameraStream):
    def __init__(self, file_name, directory, width=None, height=None, enabled=True, log_level=None, frame_skip=0,
                 loop_video=False, start_frame=0):

        if file_name is None:
            file_name = time.strftime("%H;%M;%S.avi")
        if directory is None:
            directory = time.strftime("videos/%Y_%b_%d")

        self.file_name = file_name
        self.directory = directory

        self.full_path = os.path.join(self.directory, self.file_name)

        super(VideoPlayer, self).__init__(enabled, file_name, log_level)

        self.capture = cv2.VideoCapture(self.full_path)
        self.frame_lock = Lock()
        self.paused = False
        self.frame = None

        self.fps = self.capture.get(cv2.CAP_PROP_FPS)
        self.delay = 1 / self.fps
        self.clock = Clock(self.fps)
        self.num_frames = int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT))
        if self.num_frames <= 0:
            raise FileNotFoundError("Video failed to load... No frames found!")

        self.length_sec = self.num_frames / self.fps

        self.width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.resize_frame = False

        if width is None:
            self.resize_width = self.width
        else:
            self.resize_width = width
            self.resize_frame = True

        if height is None:
            self.resize_height = self.height
        else:
            self.resize_height = height
            self.resize_frame = True

        self.current_frame = 0
        self.next_frame = 1

        self.next_frame_lock = Lock()

        self.frame_skip = frame_skip
        self.loop_video = loop_video

        if start_frame > 0:
            self.set_frame(start_frame)

    def current_pos(self):
        # return self.current_frame
        with self.frame_lock:
            return int(self.capture.get(cv2.CAP_PROP_POS_FRAMES))

    def current_time(self):
        return self.current_pos() * self.length_sec / self.num_frames

    def set_frame(self, position):
        with self.frame_lock:
            self.next_frame = position
            self.frame = None

    def get_frame(self):
        with self.frame_lock:
            return self.frame
        #     if self.frame is not None:
        #         frame = self.frame.copy()
        #     else:
        #         frame = None
        #
        # return frame

    def _set_frame(self, position):
        if position >= 0:
            if position >= self.num_frames:
                position = self.num_frames

            self.capture.set(cv2.CAP_PROP_POS_FRAMES, int(position))

    def _get_frame(self):
        if self.paused:
            return
        if self.frame_skip > 0:
            self._set_frame(self.current_pos() + self.frame_skip)

        with self.frame_lock:
            if self.next_frame - self.current_frame != 1:
                self._set_frame(self.next_frame)

            self.current_frame = self.next_frame
            self.next_frame += 1

            success, self.frame = self.capture.read()

            if not success or self.frame is None:
                if self.loop_video:
                    self.set_frame(0)
                    while success is False or self.frame is None:
                        success, self.frame = self.capture.read()
                else:
                    self.exit()
                    return
            if self.resize_frame:
                self.frame = cv2.resize(
                    self.frame, (self.resize_width, self.resize_height), interpolation=cv2.INTER_NEAREST
                )

    def run(self):
        while self.running():
            self._get_frame()
            self.update()
            # await asyncio.sleep(self.delay)
            self.clock.update()
