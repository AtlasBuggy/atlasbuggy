
try:
    import cv2
    opencv_installed = True
except ImportError:
    opencv_installed = False

if opencv_installed:
    from .camera import OpenCVCamera
    from .viewer import OpenCVViewer
    from .recorder import OpenCVRecorder
    from .video import OpenCVVideo
    from .playback import OpenCVVideoPlayback
else:
    print("Warning! Using the OpenCV module without OpenCV installed!")
from .pipeline import OpenCVPipeline
from .messages import ImageMessage
