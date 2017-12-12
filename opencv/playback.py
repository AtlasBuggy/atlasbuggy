import re
import asyncio

from atlasbuggy.log.playback import PlaybackNode
from atlasbuggy.opencv.messages import ImageMessage


class OpenCVVideoPlayback(PlaybackNode):
    def __init__(self, file_name, directory=None, enabled=True, logger=None, message_type=ImageMessage):
        super(OpenCVVideoPlayback, self).__init__(file_name, directory=directory, enabled=enabled, logger=logger)

        self.message_regex = r"ImageMessage\(t=(\d.*), n=(\d*)\)"
        self.message_type = message_type

    @asyncio.coroutine
    def parse(self, line):
        message = self.message_type.parse(line.message)
        if message is not None:
            yield from self.broadcast(message)
        else:
            self.logger.info("message not parsed: %s" % line.message)
            yield from asyncio.sleep(0.0)
