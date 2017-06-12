import os
import time
from subprocess import Popen, PIPE, DEVNULL
from atlasbuggy.cameras import VideoStream


class H264toMP4converter:
    # expects that MP4Box be installed
    def __init__(self, full_path):
        self.full_path = full_path

        ext_index = self.full_path.rfind(".")
        self.new_path = self.full_path[:ext_index]

        self.process = None
        self.output = None

    def start(self):
        print("Converting video to mp4: '%s'" % self.new_path)
        if os.path.isfile(self.new_path):
            os.remove(self.new_path)
        self.process = Popen(['MP4Box', '-add', self.full_path, self.new_path], stdin=PIPE,
                             stdout=DEVNULL, close_fds=True, bufsize=0)
        self.output = None

        assert self.process is not None

    def is_running(self):
        if self.process is not None:
            time.sleep(0.001)
            self.output = self.process.poll()

        return self.output is None


class PiVideoRecorder(VideoStream):
    def __init__(self, file_name=None, directory=None, enabled=True, log_level=None, **recorder_options):
        super(PiVideoRecorder, self).__init__(file_name, directory, enabled, log_level)
        self.options = recorder_options

        self.default_file_type = ".h264"
        self.default_length = len(self.default_file_type)
        if self.file_name.endswith(".mp4"):
            self.file_name += self.default_file_type
        self.full_path = os.path.join(self.directory, self.file_name)

    def start_recording(self):
        if self.enabled:
            self.make_dirs()
            if not self.is_recording:
                self.logger.debug("Recording video on '%s'" % self.full_path)
                self.capture.capture.start_recording(self.full_path, **self.options)
                self.is_recording = True

    def stop_recording(self):
        if self.enabled and self.is_recording:
            # self.capture.stop_recording()
            self.is_recording = False

            if self.file_name.endswith(self.default_file_type):
                self.file_name = self.file_name[:-self.default_length]

            if self.file_name.endswith(".mp4"):
                converter = H264toMP4converter(self.full_path)
                converter.start()
                while converter.is_running():
                    pass

                self.logger.debug("Conversion complete! Removing temp file: '%s'" % self.full_path)
                os.remove(self.full_path)
            else:
                self.logger.debug("Skipping conversion to mp4")
