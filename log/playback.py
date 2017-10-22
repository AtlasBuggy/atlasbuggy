import os
import time
import asyncio

from ..node import Node
from .factory import make_logger
from .parser import LogParser
from .default import default_settings


class PlaybackNode(Node):
    central_clock = 0.0

    def __init__(self, *file_names, directory=None, update_rate=None, enabled=True, logger=None):
        if logger is None:
            logger = make_logger(
                self.__class__.__name__, default_settings, write=False,
                log_format="[Playback Node][%(name)s][%(levelname)s] %(asctime)s: %(message)s")
        super(PlaybackNode, self).__init__(enabled, logger)

        self.update_rate = update_rate

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

        self.logger.info("Found %s lines in directory: %s, files: %s" % (len(self.parser.lines), directory, file_names))

    @asyncio.coroutine
    def loop(self):
        self.start_time = time.time()

        for line in self.parser:
            if self.update_rate is None:
                parser_time = time.time() - self.start_time
                if parser_time > self.current_time():
                    yield from self.parse(line)
                else:
                    yield from asyncio.sleep(0.0)
                    self.parser.skip()
            else:
                yield from self.parse(line)
                yield from asyncio.sleep(self.update_rate)

    @asyncio.coroutine
    def parse(self, line):
        yield from self.broadcast(line)

    def current_time(self):
        return self.parser.current_time()
