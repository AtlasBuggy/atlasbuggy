import re
import asyncio

from atlasbuggy.log.playback import PlaybackNode


class OpenCVVideoPlayback(PlaybackNode):
    def __init__(self, file_name, directory=None, enabled=True, logger=None):
        super(OpenCVVideoPlayback, self).__init__(file_name, directory=directory, enabled=enabled, logger=logger)

        self.message_regex = r"ImageMessage\(t=(\d.*), n=(\d*)\)"

    @asyncio.coroutine
    def parse(self, line):
        match = re.match(self.message_regex, line.message)
        if match is not None:
            # message_time = float(match.group(1))
            frame_num = int(match.group(2))

            yield from self.broadcast(frame_num)
        else:
            yield from asyncio.sleep(0.0)
