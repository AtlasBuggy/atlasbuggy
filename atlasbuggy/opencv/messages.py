import numpy as np

try:
    import cv2

    opencv_installed = True
except ImportError:
    opencv_installed = False

from atlasbuggy.message import Message


class ImageMessage(Message):
    message_regex = r"ImageMessage\(t=(\d.*), n=(\d*)\)"

    def __init__(self, image=None, n=None, width=None, height=None, depth=3, timestamp=None):
        assert type(n) == int
        assert timestamp is None or type(timestamp) == float

        self.image = image

        if (width is None or height is None) and image is not None:
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

    @classmethod
    def parse(cls, message):
        match = re.match(cls.message_regex, message)
        if match is not None:
            message_time = float(match.group(1))
            frame_num = int(match.group(2))

            return cls(n=frame_num, timestamp=message_time)
        else:
            return None

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
    message_regex = r"StereoImageMessage\(t=(\d.*), n=(\d*), dist=([-\d.e]*), lt=(\d.*), rt=(\d.*), diff=([-\d.e]*)\)"

    def __init__(self, left_image, right_image, n, separation_dist, width=None, height=None, depth=3, timestamp=None,
                 left_timestamp=None, right_timestamp=None):
        self.left_image = left_image
        self.right_image = right_image

        self.separation_dist = separation_dist
        self.left_timestamp = left_timestamp
        self.right_timestamp = right_timestamp
        self.time_diff = left_timestamp - right_timestamp

        super(StereoImageMessage, self).__init__(left_image, n, width, height, depth, timestamp)

        width, height, depth = self.get_image_dimensions(self.right_image)

        assert width == self.width, \
            "Width of left image (%s) does not match right image (%s)!!" % (self.width, width)
        assert height == self.height, \
            "Height of left image (%s) does not match right image (%s)!!" % (self.height, height)
        assert depth == self.depth, \
            "Depth of left image (%s) does not match right image (%s)!!" % (self.depth, depth)

    @classmethod
    def parse(cls, message):
        match = re.match(cls.message_regex, message)
        if match is not None:
            message_time = float(match.group(1))
            frame_num = int(match.group(2))
            separation_dist = float(match.group(3))
            left_timestamp = float(match.group(4))
            right_timestamp = float(match.group(5))

            return cls(
                None, None, frame_num, separation_dist, timestamp=message_time,
                left_timestamp=left_timestamp, right_timestamp=right_timestamp
            )
        else:
            return None

    def __str__(self):
        return "%s(t=%s, n=%s, dist=%s, lt=%s, rt=%s, diff=%s)" % (
            self.__class__.__name__, self.timestamp, self.n, self.separation_dist,
            self.left_timestamp, self.right_timestamp, self.time_diff
        )
