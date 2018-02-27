
import time
import asyncio

from atlasbuggy import Node

from .messages import ImageMessage


class OpenCVPipeline(Node):
    def __init__(self, enabled=True, logger=None):
        super(OpenCVPipeline, self).__init__(enabled, logger)

        self.paused = False

        self.capture = None
        self.capture_queue = None
        self.capture_tag = "capture"
        self.capture_sub = self.define_subscription(self.capture_tag, queue_size=1, message_type=ImageMessage,
                                                    required_attributes=("fps",))
        self.has_attributes = False
        self.has_methods = False
        self._num_frames = 0

    def take(self):
        self.capture_queue = self.capture_sub.get_queue()
        self.capture = self.capture_sub.get_producer()

        self.has_attributes = self.producer_has_attributes(self.capture_sub, "num_frames")
        self.has_methods = self.producer_has_attributes(self.capture_sub, "set_pause")

    def set_pause(self, state):
        self.capture_sub.enabled = not state
        if self.has_methods:
            self.capture.set_pause(state)
        self.paused = state

    def get_pause(self):
        return self.paused

    @property
    def num_frames(self):
        if self.has_attributes:
            return self.capture.num_frames
        else:
            return self._num_frames

    @property
    def fps(self):
        return self.capture.fps

    @asyncio.coroutine
    def loop(self):
        while True:
            while not self.capture_queue.empty():
                message = yield from self.capture_queue.get()
                self.logger.debug("pipeline_message image received: %s" % message)
                self.logger.debug("receive delay: %ss" % (time.time() - message.timestamp))

                image = yield from self.pipeline(message)
                if image is None:
                    image = message.image
                pipeline_message = ImageMessage(image, n=message.n)
                self.logger.debug("pipeline delay: %ss" % (pipeline_message.timestamp - message.timestamp))

                self._num_frames = message.n

                yield from self.broadcast(pipeline_message)
            yield from asyncio.sleep(0.5 / self.capture.fps)

    @asyncio.coroutine
    def pipeline(self, message):
        raise NotImplementedError("Please override this method.")
