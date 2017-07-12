from atlasbuggy import Robot
from atlasbuggy.subscriptions import *
from atlasbuggy.cameras.viewer import CameraViewerWithTrackbar
from atlasbuggy.cameras.videoplayer import VideoPlayer

robot = Robot()

viewer = CameraViewerWithTrackbar()
video = VideoPlayer(file_name="/Users/Woz4tetra/Google Drive/Atlas Docs/Media/Videos/Naboris Demo.mp4", width=800, height=500)

viewer.subscribe(Update(viewer.capture_tag, video))

robot.run(video, viewer)
