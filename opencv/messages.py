import numpy as np
try:
    import cv2
    opencv_installed = True
except ImportError:
    opencv_installed = False


from atlasbuggy.message import Message


class ImageMessage(Message):
    def __init__(self, image, n, width=None, height=None, depth=3, timestamp=None):
        assert type(n) == int
        assert timestamp is None or type(timestamp) == float

        self.image = image

        if width is None or height is None:
            self.height, self.width, = self.image.shape[:2]
            if len(self.image.shape) == 3:
                self.depth = self.image.shape[2]
        else:
            self.width = width
            self.height = height
            self.depth = depth


        super(ImageMessage, self).__init__(timestamp, n)

    def __str__(self):
        return "%s(t=%s, n=%s)" % (self.__class__.__name__, self.timestamp, self.n)

    @staticmethod
    def bytes_to_numpy(bytes_image):
        if opencv_installed:
            return cv2.imdecode(np.fromstring(bytes_image, dtype=np.uint8), 1)
        else:
            raise ImportError("OpenCV not installed. Can't convert image")

    def numpy_to_bytes(self):
        if opencv_installed:
            return cv2.imencode(".jpg", self.image)[1].tostring()
        else:
            raise ImportError("OpenCV not installed. Can't convert image")
