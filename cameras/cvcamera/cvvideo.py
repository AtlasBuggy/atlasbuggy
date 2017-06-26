import os
import cv2
from atlasbuggy import get_platform
from atlasbuggy.cameras import RecordingStream


class CvVideoRecorder(RecordingStream):
    def __init__(self, file_name=None, directory="", enabled=True, log_level=None, version="1.0", live_feed=True):
        super(CvVideoRecorder, self).__init__(file_name, directory, enabled, log_level, version)
        self.width = None
        self.height = None
        self.video_writer = None
        self.fourcc = None
        self.frame_buffer = []
        self.opened = False
        self.live_feed = live_feed
        self.required_buffer_len = 50

    def start_recording(self, width=None, height=None, fps=30.0):
        if self.enabled:
            self.make_dirs()

            self.width = width
            self.height = height
            self.fps = fps

            if self.file_name.endswith('avi'):
                codec = 'MJPG'
            elif self.file_name.endswith('mp4'):
                if get_platform() == 'mac':
                    codec = 'MP4V'
                else:
                    # TODO: Figure out mp4 recording in linux
                    # codec = 'DIVX'
                    codec = 'MJPG'
                    self.file_name = self.file_name[:-3] + "avi"
                    self.full_path = os.path.join(self.file_name, self.directory)
            else:
                raise ValueError("Invalid file format")
            self.fourcc = cv2.VideoWriter_fourcc(*codec)
            self.video_writer = cv2.VideoWriter()

            self.is_recording = True

            if not self.live_feed and self.width is not None and self.height is not None:
                self._dump_buffer()

    def record(self, frame):
        if self.enabled:
            if self.live_feed:
                if self.opened:
                    self._write(frame)
                else:
                    if len(self.frame_buffer) >= self.required_buffer_len:
                        self._dump_buffer()
                    else:
                        self.frame_buffer.append(frame)
            else:
                self._write(frame)
                self._dump_buffer()

    def _dump_buffer(self):
        if not self.opened:
            self.logger.debug(
                "Writing video to: '%s'. FPS: %0.2f, (w=%d, h=%d)" % (self.full_path, self.fps, self.width, self.height))
            self.video_writer.open(
                self.full_path, self.fourcc, self.fps, (self.width, self.height), True
            )
            while len(self.frame_buffer) > 0:
                self._write(self.frame_buffer.pop(0))
            self.opened = True

    def _write(self, frame):
        if self.height is None:
            self.height = frame.shape[0]
        if self.width is None:
            self.width = frame.shape[1]

        if frame.shape[0:2] != (self.height, self.width):
            frame = cv2.resize(frame, (self.height, self.width))

        self.num_frames += 1
        if len(frame.shape) == 2:
            self.video_writer.write(cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR))
        else:
            self.video_writer.write(frame)

    def stop_recording(self):
        if self.enabled and self.is_recording:
            if self.live_feed and not self.opened:  # if required frame buffer size hasn't been met...
                self._dump_buffer()
            self.logger.debug("Releasing video writer")
            self.video_writer.release()
            self.is_recording = False
