import os
import time
from threading import Lock

import cv2

from ...datastream import ThreadedStream


class VideoPlayer(ThreadedStream):
    loaded_videos = {}

    def __init__(self, enabled=True, log_level=None, post_while_paused=False, **load_video_args):
        super(VideoPlayer, self).__init__(enabled, None, log_level)

        self.capture = None
        self.width = None
        self.height = None
        self.fps = None
        self.length_sec = 0.0

        self.frame = None
        self.num_frames = 0
        self.frame_lock = Lock()

        self.paused = False
        self.post_while_paused = post_while_paused

        if "file_name" in load_video_args and load_video_args["file_name"] is not None:
            self.load_video(**load_video_args)
        else:
            self.paused = True

    def load_video(self, file_name, directory="", width=None, height=None, frame_skip=0,
                   loop_video=False, start_frame=0):
        with self.frame_lock:

            if file_name is None:
                file_name = time.strftime("%H;%M;%S.avi")
            if directory is None:
                directory = time.strftime("videos/%Y_%b_%d")

            self.file_name = file_name
            self.directory = directory

            self.full_path = os.path.join(self.directory, self.file_name)
            if not os.path.isfile(self.full_path):
                raise FileNotFoundError("Video File '%s' not found" % self.full_path)

            if self.full_path in VideoPlayer.loaded_videos:
                if self.capture == VideoPlayer.loaded_videos[self.full_path]:
                    self.reset_video()
                    return

                self.release_capture()
                self.capture = VideoPlayer.loaded_videos[self.full_path]
                self.reset_video()
            else:
                self.release_capture()
                self.capture = cv2.VideoCapture(self.full_path)
                VideoPlayer.loaded_videos[self.full_path] = self.capture

                if start_frame > 0:
                    self.reset_video(start_frame)

            self.frame_lock = Lock()
            self.paused = False

            self.fps = self.capture.get(cv2.CAP_PROP_FPS)
            self.delay = 1 / self.fps
            if self.delay > 0.5:
                self.delay = 0.1
            self.num_frames = int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT))
            if self.num_frames <= 0:
                raise FileNotFoundError("Video failed to load... No frames found!")

            self.length_sec = self.num_frames / self.fps

            self.resize_frame = False

            if width is None:
                self.width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
                self.resize_width = self.width
            else:
                self.resize_width = width
                self.width = width
                self.resize_frame = True

            if height is None:
                self.height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
                self.resize_height = self.height
            else:
                self.resize_height = height
                self.height = height
                self.resize_frame = True

            self.current_frame = 0
            self.next_frame = 1

            self.next_frame_lock = Lock()

            self.frame_skip = frame_skip
            self.loop_video = loop_video

            self.logger.debug(
                "Video loaded: width = %s, height = %s, resize_width = %s, resize_height = %s, fps = %s" % (
                    self.width, self.height, self.resize_width, self.resize_height, self.fps
                )
            )

    @property
    def current_frame_num(self):
        with self.frame_lock:
            result = int(self.capture.get(cv2.CAP_PROP_POS_FRAMES))
            return result

    def current_time(self):
        return self.current_frame_num * self.length_sec / self.num_frames

    def set_frame(self, position):
        with self.frame_lock:
            self.next_frame = position

    def _set_frame(self, position):
        if position >= 0:
            if position >= self.num_frames:
                position = self.num_frames

            self.capture.set(cv2.CAP_PROP_POS_FRAMES, int(position))

    def set_pause(self, state):
        self.paused = state

    def get_pause(self):
        return self.paused

    def reset_video(self, position=0):
        self.next_frame = position
        self.frame = None
        self._set_frame(self.next_frame)
        self.reset_callback()

    def _get_frame(self):
        if self.paused:
            if self.post_while_paused:
                self.set_frame(self.next_frame - 1 - self.frame_skip)  # keep the video in place
            else:
                return

        if self.frame_skip > 0:
            self._set_frame(self.current_frame_num + self.frame_skip)

        with self.frame_lock:
            if self.next_frame - self.current_frame != 1:
                self._set_frame(self.next_frame)

            self.current_frame = self.next_frame
            self.next_frame += self.frame_skip + 1

            success, self.frame = self.capture.read()
            if not success or self.frame is None:
                if self.loop_video:
                    self.logger.debug("Looping video")
                    self.reset_video()

                    while success is False or self.frame is None:
                        success, self.frame = self.capture.read()
                else:
                    self.exit()
                    return
            if self.resize_frame:
                self.frame = cv2.resize(
                    self.frame, (self.resize_width, self.resize_height), interpolation=cv2.INTER_NEAREST
                )

        self.post(self.frame)

    def reset_callback(self):
        pass

    def default_post_service(self, data):
        return data.copy()

    def run(self):
        while self.is_running():
            self._get_frame()
            time.sleep(self.delay)
            self.update()

    def stop(self):
        self.release_capture()

    def release_capture(self):
        if self.capture is not None:
            self.capture.release()
