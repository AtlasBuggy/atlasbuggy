import os

from atlasbuggy import Orchestrator, run
from atlasbuggy.opencv import OpenCVCamera, OpenCVViewer, OpenCVRecorder


class MyOrchestrator(Orchestrator):
    def __init__(self, event_loop):
        self.set_default(write=True,
                         file_name="record_video_demo.log",
                         directory=os.path.join("logs", "record_video_demo", "%(name)s"))
        super(MyOrchestrator, self).__init__(event_loop)

        self.camera = OpenCVCamera(capture_number=0)
        self.viewer = OpenCVViewer()
        self.recorder = OpenCVRecorder("video_record_demo.avi", "videos", fps=40)
        self.add_nodes(self.camera, self.viewer, self.recorder)

        self.subscribe(self.recorder.capture_tag, self.camera, self.recorder)
        self.subscribe(self.viewer.capture_tag, self.camera, self.viewer)


run(MyOrchestrator)
