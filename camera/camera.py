import cv2
import time
import numpy as np
from threading import Lock

from .. import get_platform
from ..datastream import ThreadedStream


class CameraStream(ThreadedStream):
    captures = {}
    used_captures = set()
    min_cap_num = 0
    max_cap_num = None

    def __init__(self, width=None, height=None, capture_number=None,
                 enabled=True, log_level=None, name=None, skip_count=0):
        super(CameraStream, self).__init__(enabled, name, log_level)

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
        self.frame_lock = Lock()

        self.paused = False

        self.skip_count = skip_count

        self.key = -1
        platform = get_platform()
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

    def update_key_codes(self, **new_key_codes):
        self.key_codes.update(new_key_codes)

    def start(self):
        if not self.enabled:
            return

        if self.capture_number is None:
            capture, height, width = self.launch_selector()
            if capture is None:
                raise FileNotFoundError(capture)
            self.capture = capture
        else:
            self.capture = self.load_capture(self.capture_number)
            success, frame = self.capture.read()
            if not success:
                raise FileNotFoundError("CameraStream %s failed to load!" % self.capture_number)
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

    @property
    def current_frame_num(self):
        return self.num_frames

    def launch_selector(self):
        selector_window_name = "Select camera for: " + self.name
        selected_capture = None
        current_capture = None
        current_num = 0
        width = None
        height = None

        while current_num in CameraStream.used_captures:
            current_num += 1

            if CameraStream.max_cap_num is not None and current_num > CameraStream.max_cap_num:
                return "No cameras left!", height, width

            try:
                current_capture = self.load_capture(current_num)
                success, frame = current_capture.read()
                if not success:
                    raise cv2.error
            except cv2.error:
                CameraStream.max_cap_num = current_num - 1
                current_capture.release()
                return "No cameras left!", height, width

        current_capture = self.load_capture(current_num)

        while selected_capture is None:
            key = self.key_pressed()

            if key == "left":
                current_num -= 1
                if current_num < CameraStream.min_cap_num:
                    current_num = CameraStream.min_cap_num
                    self.logger.warning("CameraStream failed to load! CameraStream number lower limit:", current_num)
                    continue
                while current_num in CameraStream.used_captures:
                    current_num -= 1

                current_capture = self.load_capture(current_num)

            elif key == "right":
                current_num += 1
                if CameraStream.max_cap_num is not None and current_num > CameraStream.max_cap_num:
                    self.logger.warning("CameraStream failed to load! CameraStream number upper limit:", current_num)
                    current_num = CameraStream.max_cap_num
                    continue

                while current_num in CameraStream.used_captures:
                    current_num += 1

                try:
                    current_capture = self.load_capture(current_num)
                    success, frame = current_capture.read()
                    cv2.imshow(selector_window_name, frame)
                except cv2.error:
                    self.logger.warning("CameraStream failed to load! CameraStream number upper limit:", current_num)
                    if current_num in CameraStream.captures:
                        current_capture.release()
                        del CameraStream.captures[current_num]
                    current_num -= 1
                    CameraStream.max_cap_num = current_num
                    current_capture = self.load_capture(current_num)

            elif key == "\n" or key == "\r":
                selected_capture = current_capture
                CameraStream.used_captures.add(current_num)
                self.logger.info("Using capture #%s for %s" % (current_num, self.name))

            elif key == 'q':
                selected_capture = None
                break

            success, frame = current_capture.read()
            cv2.imshow(selector_window_name, frame)
            height, width = frame.shape[0:2]
        cv2.destroyWindow(selector_window_name)
        return selected_capture, height, width

    def load_capture(self, arg):
        if arg not in CameraStream.captures:
            self.logger.info("Loading capture '%s'" % arg)
            CameraStream.captures[arg] = cv2.VideoCapture(arg)
        return CameraStream.captures[arg]

    def key_pressed(self, delay=1):
        if not self.enabled:
            return 255
        key = cv2.waitKey(delay) % 255
        if key != 255:
            if key in self.key_codes:
                self.key = self.key_codes[key]
            elif 0 <= key < 0x100:
                self.key = chr(key)
            else:
                self.logger.warning("Unrecognized key: " + str(key))
        else:
            self.key = key

        return self.key

    def run(self):
        while self.is_running():
            with self.frame_lock:
                success, self.frame = self.capture.read()

                if not success:
                    self.exit()
                    raise EOFError("Failed to read the frame")
                if self.resize_frame and self.frame.shape[0:2] != (self.height, self.width):
                    self.frame = cv2.resize(self.frame, (self.width, self.height))
            self.update()

            self.log_frame()
            self.poll_for_fps()
            self.post(self.frame)

            self.fps = self.fps_avg

    def poll_for_fps(self):
        if self.prev_t is None:
            self.prev_t = time.time()
            return 0.0

        self.length_sec = time.time() - self.start_time
        self.num_frames += 1
        if self.num_frames > 25:
            self.fps_sum += 1 / (time.time() - self.prev_t)
            self.fps_avg = self.fps_sum / self.num_frames
        self.prev_t = time.time()

    def default_post_service(self, frame):
        return frame.copy()

    def log_frame(self):
        self.logger.debug("frame #%s" % self.num_frames)

    def update(self):
        pass

    def stop(self):
        for cap_name, capture in CameraStream.captures.items():
            capture.release()
        CameraStream.captures = {}

    @staticmethod
    def bytes_to_numpy(frame):
        return cv2.imdecode(np.fromstring(frame, dtype=np.uint8), 1)

    @staticmethod
    def numpy_to_bytes(frame):
        return cv2.imencode(".jpg", frame)[1].tostring()
