import os
import time
from atlasbuggy import DataStream


class RecordingStream(DataStream):
    def __init__(self, file_name, directory, enabled, log_level, version):

        super(RecordingStream, self).__init__(
            enabled, file_name, log_level, version
        )

        self.capture = None
        self.is_recording = False
        self.fps = 30.0
        self.num_frames = 0

        self.set_path(file_name, directory)

    def set_path(self, file_name=None, directory=None):
        if file_name is None:
            file_name = time.strftime("%H;%M;%S.avi")
            if directory is None:
                # only use default if both directory and file_name are None.
                # Assume file_name has the full path if directory is None
                directory = time.strftime("videos/%Y_%b_%d")

        self.file_name = file_name
        self.directory = directory

        ext_index = self.file_name.rfind(".")
        if ext_index == -1:
            raise ValueError("An extension is required: %s" % self.file_name)

        self.full_path = os.path.join(self.directory, self.file_name)

    def make_dirs(self):
        if self.directory is not None and len(self.directory) > 0 and not os.path.isdir(self.directory):
            os.makedirs(self.directory)
        else:
            self.logger.debug("Not making directory: '%s'" % self.directory)

    def start_recording(self):
        pass

    def record(self, frame):
        pass

    def stop_recording(self):
        pass
