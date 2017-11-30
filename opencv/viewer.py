import cv2
import sys
import time
import asyncio
import numpy as np

from atlasbuggy import Node

from .messages import ImageMessage


class OpenCVViewer(Node):
    def __init__(self, enabled=True, logger=None, enable_trackbar=False, draw_while_paused=False,
                 producer_service="default"):
        super(OpenCVViewer, self).__init__(enabled, logger)

        if self.enabled:
            cv2.namedWindow(self.name)

        self.slider_name = "frame:"
        self.slider_ticks = 0
        self.current_frame_num = 0
        self.slider_current_pos = 0

        self.frame = None

        self.trackbar_enabled = enable_trackbar
        self.draw_while_paused = draw_while_paused

        platform = OpenCVViewer.get_platform()
        if platform == "linux":
            self.key_codes = {
                65362: "up",
                65364: "down",
                65361: "left",
                65363: "right",
            }
        elif platform == "mac":
            self.key_codes = {
                63232: "up",
                63233: "down",
                63234: "left",
                63235: "right",
            }
        else:
            self.key_codes = {}

        self.key = 255

        if enable_trackbar:
            self.capture_required_attributes = "num_frames",
            self.capture_required_methods = "set_pause", "get_pause", "set_frame"
        else:
            self.capture_required_attributes = None
            self.capture_required_methods = None

        self.capture_tag = "capture"
        self.capture = None
        self.capture_queue = None
        self.capture_sub = self.define_subscription(
            self.capture_tag, producer_service, message_type=ImageMessage, queue_size=1,
            required_attributes=self.capture_required_attributes,
            required_methods=self.capture_required_methods)

    def take(self):
        self.capture = self.capture_sub.get_producer()
        self.capture_queue = self.capture_sub.get_queue()

    @asyncio.coroutine
    def setup(self):
        self.initialize_trackbar()
        blank = np.zeros((300, 300))
        cv2.imshow(self.name, blank)

    def initialize_trackbar(self):
        if self.trackbar_enabled:
            self.slider_ticks = self.capture.num_frames
            if self.slider_ticks > 500:
                self.slider_ticks = 500

            if self.slider_ticks > self.capture.num_frames:
                self.slider_ticks = self.capture.num_frames

            cv2.createTrackbar(self.slider_name, self.name, 0, self.slider_ticks, self._on_slider)

    def _on_slider(self, slider_index):
        if self.trackbar_enabled:
            slider_frame_num = int(slider_index * self.capture.num_frames / self.slider_ticks)
            if abs(slider_frame_num - self.current_frame_num) > 3:
                self.set_frame(slider_frame_num)
                self.on_slider(slider_index)
                self.slider_current_pos = slider_index

    def increment_slider(self):
        if self.trackbar_enabled:
            self.slider_current_pos += 1
            cv2.setTrackbarPos(self.slider_name, self.name, self.slider_current_pos)

    def on_slider(self, slider_index):
        pass

    def set_frame(self, frame_num):
        self.capture.set_frame(frame_num)

    def draw(self, frame):
        return frame

    @asyncio.coroutine
    def loop(self):
        while True:
            if self.key_pressed() is False:
                return

            if type(self.capture.fps) == float or type(self.capture.fps) == int:
                yield from asyncio.sleep(0.5 / self.capture.fps)  # operate faster than the camera
            else:
                yield from asyncio.sleep(0.01)

            self.logger.debug("getting frame")
            if self.capture_queue.empty():
                continue
            else:
                self.increment_slider()
                message = yield from self.capture_queue.get()
                self.logger.info("viewer delay: %ss" % (time.time() - message.timestamp))
                self.logger.info("viewer image received: %s" % message)

                frame = self.draw(message.image)

            if frame is None:
                continue

            cv2.imshow(self.name, frame)

    @staticmethod
    def get_platform():
        """Use for platform specific operations"""
        if sys.platform.startswith('darwin'):  # OS X
            return "mac"
        elif (sys.platform.startswith('linux') or sys.platform.startswith(
                'cygwin')):
            return "linux"
        elif sys.platform.startswith('win'):  # Windows
            return "windows"
        else:
            return None

    def key_pressed(self, delay=1):
        if not self.enabled:
            return
        self.logger.debug("getting key")
        key = cv2.waitKey(delay)
        if key > -1:
            self.logger.debug("OpenCV key: '%s'" % key)
            if key > 0x100000:
                key -= 0x100000
            if key in self.key_codes:
                self.key = self.key_codes[key]
            elif 0 <= key < 0x100:
                self.key = chr(key)
            else:
                self.logger.warning(("Unrecognized key: " + str(key)))

            self.logger.info("Interpreted key: '%s'" % self.key)
            return self.key_down(self.key)

    def key_down(self, key):
        if key == 'q':
            return False
