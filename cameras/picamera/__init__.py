import time
import picamera
from picamera.array import PiRGBArray
from atlasbuggy.cameras import CameraStream


class PiCamera(CameraStream):
    def __init__(self, enabled=True, name=None, log_level=None):
        super(PiCamera, self).__init__(enabled, name, log_level)

        if self.enabled:
            self.capture = picamera.PiCamera()
            self.init_cam(self.capture)

            # update values based on init_cam
            self.width = self.capture.resolution[0]
            self.height = self.capture.resolution[1]
            self.fps = self.capture.framerate
        else:
            self.width = 0
            self.height = 0
            self.fps = 32

    def init_cam(self, camera):
        pass

    def run(self):
        with self.capture:
            # let camera warm up
            self.capture.start_preview()
            time.sleep(2)

            self.recorder.start_recording()

            raw_capture = PiRGBArray(self.capture, size=self.capture.resolution)
            for frame in self.capture.capture_continuous(raw_capture, format="bgr", use_video_port=True):
                with self.frame_lock:
                    self.frame = frame.array
                    raw_capture.truncate(0)
                    self.num_frames += 1
                    # self.recorder.record(self.frame)

                self.poll_for_fps()
                self.log_frame()

                while self.paused:
                    time.sleep(0.1)

                if not self.running():
                    self.recorder.stop_recording()
                    return

    def get_bytes_frame(self):
        with self.frame_lock:
            self.bytes_frame = self.numpy_to_bytes(self.frame)
        return self.bytes_frame

    def stop(self):
        # self.capture.stop_preview()  # picamera complains when this is called while recording
        self.recorder.stop_recording()
