import os
import cv2
import time
import asyncio
from atlasbuggy import Node

from .messages import ImageMessage


class OpenCVVideo(Node):
    loaded_videos = {}

    def __init__(self, enabled=True, broadcast_while_paused=False, logger=None, bind_to_playback_node=False,
                 **load_video_args):
        super(OpenCVVideo, self).__init__(enabled, logger)

        self.capture = None
        self.width = None
        self.height = None
        self.fps = None
        self.length_sec = 0.0

        self.frame = None
        self.num_frames = 0

        self.paused = False
        self.broadcast_while_paused = broadcast_while_paused
        self.bind_to_playback_node = bind_to_playback_node

        if "file_name" in load_video_args and load_video_args["file_name"] is not None:
            self.load_video(**load_video_args)
        else:
            self.paused = True

        self.playback_tag = "playback"
        self.playback_queue = None
        self.playback_sub = self.define_subscription(self.playback_tag, is_required=bind_to_playback_node,
                                                     message_type=int)

    def take(self):
        if self.is_subscribed(self.playback_tag):
            self.playback_queue = self.playback_sub.get_queue()

    def load_video(self, file_name, directory="", width=None, height=None, frame_skip=0,
                   loop_video=False, start_frame=0):
        if self.capture is not None and self.bind_to_playback_node:
            raise RuntimeError("Can't load another video! This node is bound to a playback node")

        if file_name is None:
            file_name = time.strftime("%H;%M;%S.avi")
        if directory is None:
            directory = time.strftime("videos/%Y_%b_%d")

        self.file_name = file_name
        self.directory = directory

        self.full_path = os.path.join(self.directory, self.file_name)
        if not os.path.isfile(self.full_path):
            raise FileNotFoundError("Video File '%s' not found" % self.full_path)

        if self.full_path in OpenCVVideo.loaded_videos:
            if self.capture == OpenCVVideo.loaded_videos[self.full_path]:
                self.reset_video()
                return

            self.release_capture()
            self.capture = OpenCVVideo.loaded_videos[self.full_path]
            self.reset_video()
        else:
            self.release_capture()
            self.capture = cv2.VideoCapture(self.full_path)
            OpenCVVideo.loaded_videos[self.full_path] = self.capture

            if start_frame > 0:
                self.reset_video(start_frame)

        self.paused = False

        self.fps = self.capture.get(cv2.CAP_PROP_FPS)
        self.delay = 1 / self.fps
        if self.delay > 0.1:
            self.delay = 0.1
        self.num_frames = int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT))
        if self.num_frames <= 0:
            raise FileNotFoundError("Video failed to load... No frames found!")

        self.length_sec = self.num_frames / self.fps

        self.resize_frame = False

        if width is None:
            self.width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.resize_width = self.width
        else:
            self.resize_width = width
            self.width = width
            self.resize_frame = True

        if height is None:
            self.height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.resize_height = self.height
        else:
            self.resize_height = height
            self.height = height
            self.resize_frame = True

        self.current_frame = 0
        self.next_frame = 1

        self.frame_skip = frame_skip
        self.loop_video = loop_video

        self.logger.debug(
            "Video loaded: width = %s, height = %s, resize_width = %s, resize_height = %s, fps = %s" % (
                self.width, self.height, self.resize_width, self.resize_height, self.fps
            )
        )

    def current_frame_num(self):
        return int(self.capture.get(cv2.CAP_PROP_POS_FRAMES))

    def current_time(self):
        return self.current_frame_num() * self.length_sec / self.num_frames

    def set_frame(self, position):
        if position >= 0:
            if position >= self.num_frames:
                position = self.num_frames

            self.capture.set(cv2.CAP_PROP_POS_FRAMES, int(position))

    def set_pause(self, state):
        self.paused = state

    def get_pause(self):
        return self.paused

    def reset_video(self, position=0):
        self.next_frame = position
        self.frame = None
        self.set_frame(self.next_frame)
        self.reset_callback()

    def reset_callback(self):
        pass

    @asyncio.coroutine
    def loop(self):
        while True:
            if self.paused:
                if self.broadcast_while_paused:
                    self.set_frame(self.next_frame - 1 - self.frame_skip)  # keep the video in place
                else:
                    return

            if self.is_subscribed(self.playback_tag):
                while not self.playback_queue.empty():
                    self.next_frame = yield from self.playback_queue.get()
                    if self.next_frame - self.current_frame != 1:
                        self.set_frame(self.next_frame)
                    success = yield from self.load_frame()
                    if not success:
                        return
                    self.current_frame = self.next_frame

                yield from asyncio.sleep(0.0)
            else:
                if self.frame_skip > 0:
                    self.set_frame(self.current_frame_num() + self.frame_skip)

                if self.next_frame - self.current_frame != 1:
                    self.set_frame(self.next_frame)

                self.logger.info("frame #%s of %s" % (self.current_frame, self.num_frames))

                self.current_frame = self.next_frame
                self.next_frame += self.frame_skip + 1

                success = yield from self.load_frame()
                if not success:
                    return

    @asyncio.coroutine
    def load_frame(self):
        success, self.frame = self.capture.read()
        if not success or self.frame is None:
            if self.loop_video:
                self.logger.info("Looping video")
                self.reset_video()

                while success is False or self.frame is None:
                    success, self.frame = self.capture.read()
            else:
                return False
        if self.resize_frame:
            self.frame = cv2.resize(
                self.frame, (self.resize_width, self.resize_height), interpolation=cv2.INTER_NEAREST
            )

        message = ImageMessage(self.frame, time.time(), self.current_frame_num())
        self.logger.info("video image received: %s" % message)
        yield from self.broadcast(message)
        yield from asyncio.sleep(self.delay)
        return True

    def stop(self):
        self.release_capture()

    def release_capture(self):
        if self.capture is not None:
            self.capture.release()
