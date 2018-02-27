import os
import asyncio

from atlasbuggy import Orchestrator, run
from atlasbuggy.opencv import OpenCVCamera, OpenCVViewer, OpenCVRecorder


class MyOrchestrator(Orchestrator):
    def __init__(self, event_loop):
        self.set_default(write=True,
                         file_name="record_video_demo.log",
                         directory=os.path.join("logs", "record_video_demo", "%(name)s"))
        super(MyOrchestrator, self).__init__(event_loop)

        # OpenCVCamera.ignore_capture_numbers(0)
        self.camera = OpenCVCamera()
        self.viewer = OpenCVViewer()
        self.recorder = OpenCVRecorder("video_record_demo.avi", "videos")
        self.add_nodes(self.camera, self.recorder, self.viewer)

        self.subscribe(self.camera, self.recorder, self.recorder.capture_tag)
        self.subscribe(self.camera, self.viewer, self.viewer.capture_tag)


run(MyOrchestrator)
