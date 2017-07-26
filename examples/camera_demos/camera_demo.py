import cv2
import numpy as np

from atlasbuggy import Robot
from atlasbuggy.subscriptions import *
from atlasbuggy.camera import CameraViewer, CameraStream, VideoRecorder, Pipeline
from atlasbuggy import AsyncStream


class MyPipeline(Pipeline):
    def __init__(self, enabled=True, log_level=None):
        super(MyPipeline, self).__init__(enabled, log_level)

        self.results_service_tag = "results"
        self.add_service(self.results_service_tag, self.results_post_service)

    def results_post_service(self, data):
        return data

    def pipeline(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        laplacian_64f = cv2.Laplacian(gray, cv2.CV_16S, ksize=5, scale=0.5, delta=0)
        abs_laplacian_64f = np.absolute(laplacian_64f)
        laplacian_8u = np.uint8(abs_laplacian_64f)

        self.post(self.current_frame_num, self.results_service_tag)

        return np.concatenate((cv2.cvtColor(laplacian_8u, cv2.COLOR_GRAY2BGR), frame), axis=1)


class DummyConsumer(AsyncStream):
    def __init__(self):
        super(DummyConsumer, self).__init__(True)

        self.pipeline_feed = None
        self.pipeline_tag = "pipeline"
        self.pipeline_service_tag = "results"
        self.require_subscription(self.pipeline_tag, Feed, MyPipeline, self.pipeline_service_tag)

    def take(self, subscriptions):
        self.pipeline_feed = subscriptions[self.pipeline_tag].get_feed()

    async def run(self):
        while self.is_running():
            while not self.pipeline_feed.empty():
                results = await self.pipeline_feed.get()
                self.pipeline_feed.task_done()
                self.logger.info("results: %s" % results)
            await asyncio.sleep(0.1)

robot = Robot(write=False)

recorder = VideoRecorder()
camera = CameraStream(capture_number=0, width=800, height=500)
viewer = CameraViewer(enable_trackbar=False)
pipeline = MyPipeline()
dummy = DummyConsumer()

recorder.subscribe(Feed(recorder.capture_tag, pipeline))
# recorder.subscribe(Feed(recorder.capture_tag, camera))
viewer.subscribe(Update(viewer.capture_tag, pipeline))
pipeline.subscribe(Update(pipeline.capture_tag, camera))
dummy.subscribe(Feed(dummy.pipeline_tag, pipeline, dummy.pipeline_service_tag))

robot.run(viewer, camera, pipeline, recorder, dummy)
