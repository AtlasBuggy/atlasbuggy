from atlasbuggy import Robot
from atlasbuggy.subscriptions import *
from atlasbuggy.camera import CameraViewer
from atlasbuggy.camera import VideoPlayer

robot = Robot(write=False)

viewer = CameraViewer()
video = VideoPlayer(file_name="...", width=800, height=500)

viewer.subscribe(Update(viewer.capture_tag, video))

robot.run(video, viewer)
