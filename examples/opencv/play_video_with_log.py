from atlasbuggy import Orchestrator, run
from atlasbuggy.opencv import OpenCVViewer, OpenCVVideo, OpenCVVideoPlayback


class MyOrchestrator(Orchestrator):
    def __init__(self, event_loop):
        super(MyOrchestrator, self).__init__(event_loop)

        self.video_log = OpenCVVideoPlayback("logs/record_video_demo/OpenCVCamera/record_video_demo.log")
        self.video = OpenCVVideo(file_name="videos/video_record_demo.avi", bind_to_playback_node=True)
        self.viewer = OpenCVViewer()
        self.add_nodes(self.video, self.viewer, self.video_log)

        self.subscribe(self.viewer.capture_tag, self.video, self.viewer)
        self.subscribe(self.video.playback_tag, self.video_log, self.video)


run(MyOrchestrator)
