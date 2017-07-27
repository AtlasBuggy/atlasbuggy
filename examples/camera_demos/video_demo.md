# Video Player
Assuming you have the dependencies set up and have followed the installation instructions, let's dive in! This demo assumes you have opencv 3 installed. Make a new python file and call it "video_demo.py" or whatever you want.

First, you'll want to import Robot. This class manages all the components of our robot.
```python
from atlasbuggy import Robot
```

Next we'll want to initialize the robot
```python
robot = Robot()
```

We want this to be a simple video player, so let's import the video player stream. Put all your imports at the top of the file.

```python
from atlasbuggy.cameras.videoplayer import VideoPlayer
```

Initialize the video player stream. It's important to put this after initializing the robot. Replace ```"..."``` with a path to a video. You can't resize the window after it launches, so put a small-ish width and height.
```python
video = VideoPlayer(file_name="...", width=800, height=500)
```

Next we'll want a way to view the video, so let's import a viewer stream. There a basic viewer, CameraViewer, and a featured viewer, CameraViewerWithTrackbar. CameraViewerWithTrackbar works out of the box while CameraViewer requires subclassing to function.
```python
from atlasbuggy.cameras.viewer import CameraViewerWithTrackbar  # put this at the top

viewer = CameraViewerWithTrackbar()  # put this below robot's definition
```

Now we need to tell the viewer where the video source is. First import subscriptions,
```python
from atlasbuggy.subscriptions import *
```

then link the viewer and the video.
```python
viewer.subscribe(Update(viewer.capture_tag, video))
```

Let me explain what's going on. CameraViewerWithTrackbar requires a subscription which is explicitly defined in its constructor (atlasbuggy/cameras/viewer/trackbar.py and see for yourself). A subscription is essential a data pipe that two data streams share. When the viewer "subscribes" to the video player, the viewer is now listening for data from the video player.

Update is a subscription type that defines one possible relationship these two streams can have. This subscription type acts like a mailbox. The video player "posts" one frame of the video in the mailbox. The viewer sees that there is something new in the mailbox so it "get"'s it. Get and post are the names of methods used in this process. If the video player adds a new frame before the viewer can grab it, the video player discards the old frame and replaces it with a new one. This is so the viewer doesn't get behind when displaying frames.

capture\_tag is a property of CameraViewerWithTrackbar. Most data streams define the subscription tag with \<something\>_tag. Check the stream's documentation for that.

The last step is to tell the robot to run.
```python
robot.run(video, viewer)
```

To make sure the viewer displays every single frame the video player posts, try replacing Update with Feed. Under the hood, this is a shared Queue object. The first object in will be the first out (FIFO). If you're waiting in line, you're in a queue. The first person to get in line will be the first person who gets out of the line. Try changing Update to Feed. Notice how when you click the trackbar, the jump isn't as instantaneous. The viewer needs to catch up to the video.

This example is in atlasbuggy/examples.

So let's break that down. We initialized the Robot class before all our data streams, we initialized all the data streams we wanted the robot to run, we defined how streams pass data to each other with subscriptions, and we told the robot to run both the viewer and the video player.

Simple as that! Check the examples folder for more complex video viewers like adding your own key mappings and applying your own opencv filters to the video.

Return to the main readme for the next example: [README.md](../../README.md)