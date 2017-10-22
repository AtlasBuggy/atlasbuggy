from atlasbuggy import Orchestrator, run
from atlasbuggy.opencv import OpenCVViewer, OpenCVVideo


class MyOrchestrator(Orchestrator):
    def __init__(self, event_loop):
        super(MyOrchestrator, self).__init__(event_loop)

        self.video = OpenCVVideo(file_name="videos/video_record_demo.avi")
        self.viewer = OpenCVViewer(enable_trackbar=True)
        self.add_nodes(self.video, self.viewer)

        self.subscribe(self.viewer.capture_tag, self.video, self.viewer)

run(MyOrchestrator)