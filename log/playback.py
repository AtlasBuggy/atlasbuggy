import os
import asyncio

from node import Node
from log.factory import make_logger
from log.parser import LogParser
from log.default import default_settings


class PlaybackNode(Node):
    def __init__(self, *file_names, directory=None, realtime=True, enabled=True, logger=None):
        if logger is None:
            logger = make_logger(
                self.__class__.__name__, default_settings, write=False,
                log_format="[playback][%(name)s][%(levelname)s] %(asctime)s: %(message)s")
        super(PlaybackNode, self).__init__(enabled, logger)

        self.realtime = realtime

        self.parser = None
        if len(file_names) == 0:
            raise ValueError("No file names given!!")
        for file_name in file_names:
            if directory is not None:
                path = os.path.join(file_name, directory)
            else:
                path = file_name
            with open(path) as log_file:
                new_parser = LogParser(log_file.read())
            if self.parser is None:
                self.parser = new_parser
            else:
                self.parser.append_log(new_parser)

    @asyncio.coroutine
    def loop(self):
        for line in self.parser:
            yield from self.parse(line)
            if self.realtime:
                yield from asyncio.sleep(self.parser.delta_t())

    @asyncio.coroutine
    def parse(self, line):
        yield from self.broadcast(line)

    def current_time(self):
        return self.parser.current_time()
