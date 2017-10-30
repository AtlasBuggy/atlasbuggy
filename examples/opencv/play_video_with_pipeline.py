import cv2

from atlasbuggy import Orchestrator, run
from atlasbuggy.opencv import OpenCVViewer, OpenCVVideo, OpenCVVideoPlayback, OpenCVPipeline


class MyPipeline(OpenCVPipeline):
    def __init__(self, enabled=True, logger=None):
        super(MyPipeline, self).__init__(enabled, logger=logger)

    def pipeline(self, image):
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        threshold_value, image = cv2.threshold(image, 0, 255, cv2.THRESH_OTSU)
        return image


class MyOrchestrator(Orchestrator):
    def __init__(self, event_loop):
        super(MyOrchestrator, self).__init__(event_loop)

        self.video_log = OpenCVVideoPlayback("logs/record_video_demo/OpenCVCamera/record_video_demo.log")
        self.video = OpenCVVideo(file_name="videos/video_record_demo.avi")
        self.viewer = OpenCVViewer()
        self.pipeline = MyPipeline()

        self.add_nodes(self.video, self.viewer, self.video_log, self.pipeline)

        self.subscribe(self.pipeline, self.viewer, self.viewer.capture_tag)
        self.subscribe(self.video_log, self.video, self.video.playback_tag)
        self.subscribe(self.video, self.pipeline, self.pipeline.capture_tag)

run(MyOrchestrator)
