import cv2
import asyncio
import numpy as np

from .base import BaseViewer
from ...subscriptions import Update


class CameraViewer(BaseViewer):
    def __init__(self, enabled=True, log_level=None, name=None, enable_trackbar=True, draw_while_paused=False):
        super(CameraViewer, self).__init__(enabled, log_level, name)

        self.slider_name = "frame:"
        self.slider_ticks = 0
        self.current_frame_num = 0
        self.slider_current_pos = 0

        self.frame = None

        if enable_trackbar:
            required_attributes = "width", "height", "num_frames", "set_pause", \
                                  "get_pause", "current_frame_num", "set_frame"
        else:
            required_attributes = None

        self.capture_tag = "capture"
        self.capture = None
        self.capture_feed = None
        self.require_subscription(self.capture_tag, Update, required_attributes=required_attributes)

        self.trackbar_enabled = enable_trackbar
        self.draw_while_paused = draw_while_paused

    def take(self, subscriptions):
        self.take_capture(subscriptions)

    def take_capture(self, subscriptions):
        self.capture = subscriptions[self.capture_tag].get_stream()
        self.capture_feed = subscriptions[self.capture_tag].get_feed()

    def started(self):
        self.initialize_trackbar()
        blank = np.zeros((300, 300))
        cv2.imshow(self.name, blank)

    def initialize_trackbar(self):
        if self.trackbar_enabled:
            self.slider_ticks = self.capture.width // 3

            if self.slider_ticks > self.capture.num_frames:
                self.slider_ticks = self.capture.num_frames

            cv2.createTrackbar(self.slider_name, self.name, 0, self.slider_ticks, self._on_slider)

            min_fps = 45
            if self.capture.fps >= min_fps:
                self.delay = 1 / self.capture.fps
            else:
                self.delay = 1 / min_fps

    def _on_slider(self, slider_index):
        if self.trackbar_enabled:
            slider_frame_num = int(slider_index * self.capture.num_frames / self.slider_ticks)
            if abs(slider_frame_num - self.current_frame_num) > 3:
                self.set_frame(slider_frame_num)

                self.on_slider(slider_index)

    def on_slider(self, slider_index):
        pass

    def set_frame(self, frame_num):
        self.capture.set_frame(frame_num)

    def get_frame_from_feed(self):
        return self.capture_feed.get()

    def get_frame(self):
        if self.capture_feed.empty():
            return None
        else:
            self.current_frame_num = self.capture.current_frame_num
            # self.increment_slider()
            return self.draw(self.get_frame_from_feed())

    def draw(self, frame):
        return frame

    def update_slider_pos(self, position=None):
        if self.trackbar_enabled:
            if position is None:
                position = int(self.capture.current_frame_num * self.slider_ticks / self.capture.num_frames)
            self.slider_current_pos = position
            cv2.setTrackbarPos(self.slider_name, self.name, self.slider_current_pos)

    def increment_slider(self):
        self.slider_current_pos += 1
        cv2.setTrackbarPos(self.slider_name, self.name, self.slider_current_pos)

    def show_frame(self):
        """
        Display the frame in the Capture's window using cv2.imshow
        :param frame: A numpy array containing the image to be displayed
                (shape = (height, width, 3))
        :return: None
        """
        self.key_pressed()

        if not self.is_paused() or self.draw_while_paused:
            frame = self.get_frame()

            if frame is None:
                return

            cv2.imshow(self.name, frame)

    def toggle_pause(self):
        self.capture.set_pause(not self.capture.get_pause())

    def is_paused(self):
        return self.capture.get_pause()

    def key_down(self, key):
        if key == 'q':
            self.exit()
        elif key == ' ':
            self.toggle_pause()
