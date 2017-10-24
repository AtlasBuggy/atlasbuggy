from atlasbuggy import Orchestrator, run
from atlasbuggy.opencv import OpenCVCamera, OpenCVViewer


class MyOrchestrator(Orchestrator):
    def __init__(self, event_loop):
        super(MyOrchestrator, self).__init__(event_loop)

        self.camera = OpenCVCamera(capture_number=0)
        self.viewer = OpenCVViewer()
        self.add_nodes(self.camera, self.viewer)

        self.subscribe(self.camera, self.viewer, self.viewer.capture_tag)

run(MyOrchestrator)