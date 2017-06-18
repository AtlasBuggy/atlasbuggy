import cv2
import asyncio
from atlasbuggy.datastream import AsyncStream
from atlasbuggy import get_platform


class CameraViewer(AsyncStream):
    def __init__(self, enabled=True, log_level=None, name=None, enable_slider=False):

        super(CameraViewer, self).__init__(enabled, name, log_level)

        if self.enabled:
            cv2.namedWindow(self.name)

        self.key = -1
        self.slider_pos = 0
        self.slider_name = "frame:"
        self.enable_slider = enable_slider
        self.slider_ticks = 0

        self.capture = None
        self.pipeline = None

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

    def take(self):
        self.capture = self.streams["capture"]
        if "pipeline" in self.streams:
            self.pipeline = self.streams["pipeline"]

        self.slider_ticks = int(self.capture.capture.get(cv2.CAP_PROP_FRAME_WIDTH) // 3)
        if self.slider_ticks > self.capture.num_frames:
            self.slider_ticks = self.capture.num_frames

        if self.enabled and self.enable_slider:
            cv2.createTrackbar(self.slider_name, self.name, 0, self.slider_ticks, self.on_slider)

    def update_key_codes(self, **new_key_codes):
        self.key_codes.update(new_key_codes)

    async def run(self):
        if not self.enabled:
            return
        while self.running():
            self.show_frame()
            self.update()
            await asyncio.sleep(0.1 / self.capture.fps)

    def update(self):
        pass

    def _on_slider(self, slider_index):
        slider_pos = int(slider_index * self.capture.num_frames / self.slider_ticks)
        if abs(slider_pos - self.capture.current_pos()) > 1:
            self.capture.set_frame(slider_pos)
            # self.show_frame()
            self.slider_pos = slider_index
            self.on_slider(slider_index)

    def on_slider(self, slider_index):
        pass

    def show_frame(self):
        """
        Display the frame in the Capture's window using cv2.imshow
        :param frame: A numpy array containing the image to be displayed
                (shape = (height, width, 3))
        :return: None
        """
        if self.pipeline is None or not self.pipeline.enabled:
            frame = self.capture.get_frame()
        else:
            frame = self.pipeline.frame

        if frame is None:
            return

        cv2.imshow(self.name, frame)
        self.key_pressed()

    def key_pressed(self, delay=1):
        if not self.enabled:
            return -1
        key = cv2.waitKey(delay)
        if key > -1:
            if key in self.key_codes:
                self.key = self.key_codes[key]
            elif 0 <= key < 0x100:
                self.key = chr(key)
            else:
                print(("Unrecognized key: " + str(key)))

            self.key_callback(self.key)
        else:
            self.key = key

    def key_callback(self, key):
        if key == 'q':
            self.exit()

    def stop(self):
        cv2.destroyWindow(self.name)
