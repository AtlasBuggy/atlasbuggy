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
            width, height, depth = self.get_image_dimensions(image)

        self.width = width
        self.height = height
        self.depth = depth

        super(ImageMessage, self).__init__(timestamp, n)

    def get_image_dimensions(self, image):
        height, width, = image.shape[:2]
        if len(image.shape) == 3:
            depth = image.shape[2]
        else:
            depth = 1
        return width, height, depth

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


class StereoImageMessage(ImageMessage):
    def __init__(self, left_image, right_image, n, separation_dist, width=None, height=None, depth=3, timestamp=None):
        self.left_image = left_image
        self.right_image = right_image

        self.separation_dist = separation_dist

        super(StereoImageMessage, self).__init__(left_image, n, width, height, depth, timestamp)

        width, height, depth = self.get_image_dimensions(self.right_image)

        assert width == self.width, \
            "Width of left image (%s) does not match right image (%s)!!" % (self.width, width)
        assert height == self.height, \
            "Height of left image (%s) does not match right image (%s)!!" % (self.height, height)
        assert depth == self.depth, \
            "Depth of left image (%s) does not match right image (%s)!!" % (self.depth, depth)
