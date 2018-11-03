import os
import time
import inspect
import asyncio

from ..node import Node
from .parser import LogParser
from ..message import Message


class PlaybackNode(Node):
    def __init__(self, *file_names, directory=None, update_rate=None, enabled=True, logger=None, name=None, message_class=None,
                 message_parse_fn=None, parse_field_fn=None):
        self.set_logger(write=False,
                        log_format="[Playback Node][%(name)s][%(levelname)s] %(asctime)s: %(message)s")
        super(PlaybackNode, self).__init__(enabled, name, logger)

        self.update_rate = update_rate

        self.parser = None
        if len(file_names) == 0:
            raise ValueError("No file names given!!")
        for file_name in file_names:
            if directory is not None:
                path = os.path.join(directory, file_name)
            else:
                path = file_name
            with open(path) as log_file:
                new_parser = LogParser(log_file.read())
            if self.parser is None:
                self.parser = new_parser
            else:
                self.parser.append_log(new_parser)

        self.logger.info("Found %s lines in directory: %s, files: %s" % (len(self.parser.lines), directory, file_names))

        self.message_class = message_class
        if message_class is not None:
            assert inspect.isclass(message_class), "Input message type isn't a class! '%s'" % message_class
            self.is_type_message = issubclass(message_class, Message)
            self.message_class(0.0, 0)  # create at least one instance incase auto_serialize is called in constructor
            if parse_field_fn is not None:
                self.message_class.parse_field = parse_field_fn
        else:
            self.is_type_message = False
        self.message_parse_fn = message_parse_fn

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
        self.logger.info("Playback node complete.")
        yield from self.completed()

    @asyncio.coroutine
    def completed(self):
        pass

    @asyncio.coroutine
    def parse(self, line):
        if self.message_parse_fn is not None:
            yield from self.message_parse_fn(line)

        elif self.is_type_message:
            message = self.message_class.parse(line.message)

            if message is not None:
                yield from self.broadcast(message)
            else:
                self.logger.info("'%s' said: %s" % (self.name, line.message))
                yield from asyncio.sleep(0.0)

        else:
            self.logger.info("Broadcasting raw text.")
            yield from self.broadcast(line)

    def current_time(self):
        return self.parser.current_time()
