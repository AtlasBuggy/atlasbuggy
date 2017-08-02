import asyncio

import cv2

from ... import get_platform
from ...datastream import AsyncStream


class BaseViewer(AsyncStream):
    def __init__(self, enabled=True, log_level=None, name=None):

        super(BaseViewer, self).__init__(enabled, name, log_level)

        if self.enabled:
            cv2.namedWindow(self.name)

        self.delay = 0.0

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

        self.key = 255

    def update_key_codes(self, **new_key_codes):
        self.key_codes.update(new_key_codes)

    async def run(self):
        while self.is_running():
            self.show_frame()
            await self.update()

    async def update(self):
        await asyncio.sleep(self.delay)

    def get_frame(self):
        raise NotImplementedError("Please overwrite this method")

    def set_frame(self, frame_num):
        pass

    async def show_frame(self):
        """
        Display the frame in the Capture's window using cv2.imshow
        """
        self.key_pressed()

        frame = self.get_frame()

        if frame is None:
            return

        cv2.imshow(self.name, frame)

    def key_pressed(self, delay=1):
        if not self.enabled:
            return 255
        key = cv2.waitKey(delay)
        if key > -1:
            if key in self.key_codes:
                self.key = self.key_codes[key]
            elif 0 <= key < 0x100:
                self.key = chr(key)
            else:
                print(("Unrecognized key: " + str(key)))

            self.key_down(self.key)

    def key_down(self, key):
        if key == 'q':
            self.exit()

    def stop(self):
        cv2.destroyWindow(self.name)
        self.viewer_stopped()

    def viewer_stopped(self):
        pass
