import sys
import cv2
import time
import asyncio

from atlasbuggy import Node

from .messages import ImageMessage


class OpenCVCamera(Node):
    captures = {}
    used_captures = set()
    min_cap_num = 0
    max_cap_num = None

    def __init__(self, width=None, height=None, capture_number=None, enabled=True, logger=None, skip_count=0):
        super(OpenCVCamera, self).__init__(enabled, logger)
        self.capture_number = capture_number
        self.capture = None

        self.width = width
        self.height = height
        self.resize_frame = False

        self.fps = None
        self.length_sec = 0.0

        self.fps_sum = 0.0
        self.fps_avg = 30.0
        self.prev_t = None

        self.frame = None
        self.num_frames = 0

        self.paused = False

        self.skip_count = skip_count

        self.key = -1
        platform = OpenCVCamera.get_platform()
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

    @classmethod
    def ignore_capture_numbers(cls, *capture_nums):
        for capture_num in capture_nums:
            cls.used_captures.add(capture_num)

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

    def update_key_codes(self, **new_key_codes):
        self.key_codes.update(new_key_codes)

    def set_pause(self, state):
        self.paused = state

    def get_pause(self):
        return self.paused

    @asyncio.coroutine
    def setup(self):
        if not self.enabled:
            return

        if self.capture_number is None:
            self.logger.info("No capture number provided. Launching view selector...")
            capture, height, width = self.launch_selector()
            if capture is None:
                raise FileNotFoundError(capture)
            self.capture = capture
        else:
            self.capture = self.load_capture(self.capture_number)
            success, frame = self.capture.read()
            if not success:
                raise FileNotFoundError("OpenCVCamera %s failed to load!" % self.capture_number)
            height, width = frame.shape[0:2]

        if self.height is not None:
            if height != self.height:
                self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                self.resize_frame = True
        else:
            self.height = height

        if self.width is not None:
            if width != self.width:
                self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.resize_frame = True
        else:
            self.width = width

        self.fps = self.capture.get(cv2.CAP_PROP_FPS)

    def load_capture(self, arg):
        try:
            if arg not in OpenCVCamera.captures:
                self.logger.info("Loading capture '%s'" % arg)
                OpenCVCamera.captures[arg] = cv2.VideoCapture(arg)
            return OpenCVCamera.captures[arg]
        except cv2.error:
            return None

    def launch_selector(self):
        selector_window_name = "Select camera for: " + self.name
        selected_capture = None
        current_num = 0
        width = None
        height = None

        self.logger.info("Captures in use: %s" % OpenCVCamera.used_captures)
        while current_num in OpenCVCamera.used_captures:
            current_num += 1

            if OpenCVCamera.max_cap_num is not None and current_num > OpenCVCamera.max_cap_num:
                return "No cameras left!", height, width

            current_capture = self.load_capture(current_num)
            if current_num is None:
                OpenCVCamera.max_cap_num = current_num - 1
                current_capture.release()
                return "No cameras left!", height, width

            success, frame = current_capture.read()
            if not success:
                raise cv2.error

        self.logger.info("Based on used captures, loading capture number %s" % current_num)
        current_capture = self.load_capture(current_num)

        while selected_capture is None:
            key = self.key_pressed()

            if key == "left":
                current_num -= 1
                if current_num < OpenCVCamera.min_cap_num:
                    current_num = OpenCVCamera.min_cap_num
                    self.logger.warning("OpenCVCamera failed to load! OpenCVCamera number lower limit:", current_num)
                    continue
                while current_num in OpenCVCamera.used_captures:
                    current_num -= 1

                current_capture = self.load_capture(current_num)

            elif key == "right":
                current_num += 1
                if OpenCVCamera.max_cap_num is not None and current_num > OpenCVCamera.max_cap_num:
                    self.logger.warning("OpenCVCamera failed to load! OpenCVCamera number upper limit:", current_num)
                    current_num = OpenCVCamera.max_cap_num
                    continue

                while current_num in OpenCVCamera.used_captures:
                    current_num += 1

                try:
                    current_capture = self.load_capture(current_num)
                    success, frame = current_capture.read()
                    cv2.imshow(selector_window_name, frame)
                except cv2.error:
                    self.logger.warning("OpenCVCamera failed to load! OpenCVCamera number upper limit:", current_num)
                    if current_num in OpenCVCamera.captures:
                        current_capture.release()
                        del OpenCVCamera.captures[current_num]
                    current_num -= 1
                    OpenCVCamera.max_cap_num = current_num
                    current_capture = self.load_capture(current_num)

            elif key == "\n" or key == "\r":
                selected_capture = current_capture
                OpenCVCamera.used_captures.add(current_num)
                self.logger.info("Using capture #%s for %s" % (current_num, self.name))

            elif key == 'q':
                selected_capture = None
                break

            success, frame = current_capture.read()
            cv2.imshow(selector_window_name, frame)
            height, width = frame.shape[0:2]
        cv2.destroyWindow(selector_window_name)
        return selected_capture, height, width

    def key_pressed(self, delay=1):
        if not self.enabled:
            return -1
        key = cv2.waitKey(delay)
        if key != -1:
            if key > 0x100000:
                key -= 0x100000
            if key in self.key_codes:
                self.key = self.key_codes[key]
            elif 0 <= key < 0x100:
                self.key = chr(key)
            else:
                self.logger.warning("Unrecognized key: " + str(key))

            self.logger.info("Intrepreting '%s' as '%s'" % (key, self.key))
        else:
            self.key = key

        return self.key

    @asyncio.coroutine
    def loop(self):
        t0 = time.time()
        start_time = time.time()
        acquisition_rate = 3
        counter = 0
        prev_image_num = 0

        while True:
            success, self.frame = self.capture.read()

            if not success:
                raise EOFError("Failed to read the frame")
            if self.resize_frame and self.frame.shape[0:2] != (self.height, self.width):
                self.frame = cv2.resize(self.frame, (self.width, self.height))
            self.poll_for_fps()

            message = ImageMessage(self.frame, counter)
            counter += 1

            self.log_to_buffer(time.time(), message)
            t1 = time.time()
            if (t1 - t0) > acquisition_rate:
                self.logger.info("received %s images in %s seconds. %s received in total (fps=%0.1f)" % (
                    counter - prev_image_num, acquisition_rate, counter, self.fps
                ))
                t0 = time.time()

            yield from self.broadcast(message)

    def poll_for_fps(self):
        if self.prev_t is None:
            self.prev_t = time.time()
            return 0.0

        self.length_sec = time.time() - self.start_time
        self.num_frames += 1
        self.fps_sum += 1 / (time.time() - self.prev_t)
        self.fps_avg = self.fps_sum / self.num_frames
        self.prev_t = time.time()

        self.fps = self.fps_avg

    @asyncio.coroutine
    def teardown(self):
        if len(OpenCVCamera.captures) > 0:
            for cap_name, capture in OpenCVCamera.captures.items():
                capture.release()
            OpenCVCamera.captures = {}
