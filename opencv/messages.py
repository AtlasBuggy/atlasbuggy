import cv2
import numpy as np

from atlasbuggy.message import Message


class ImageMessage(Message):
    def __init__(self, image, n, timestamp=None, is_bytes=False):
        if is_bytes:
            self.image = ImageMessage.bytes_to_numpy(image)
        else:
            self.image = image

        self.height, self.width, = self.image.shape[:2]
        if len(self.image.shape) == 3:
            self.depth = self.image.shape[2]

        super(ImageMessage, self).__init__(timestamp, n)

    def __str__(self):
        return "%s(t=%s, n=%s)" % (self.__class__.__name__, self.timestamp, self.n)

    @staticmethod
    def bytes_to_numpy(bytes_image):
        return cv2.imdecode(np.fromstring(bytes_image, dtype=np.uint8), 1)

    def numpy_to_bytes(self):
        return cv2.imencode(".jpg", self.image)[1].tostring()
