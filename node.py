import asyncio
import logging
from log_factory import make_logger


class Node:
    def __init__(self, enabled=True, logger=None, name=None):
        self.enabled = enabled
        self.name = self.__class__.__name__ if name is None else name
        if logger is None:
            self.logger = make_logger(self.name, logging.DEBUG)

    @asyncio.coroutine
    def setup(self):
        yield from asyncio.sleep(0.0)
        self.logger.info("setup")

    @asyncio.coroutine
    def loop(self):
        yield from asyncio.sleep(0.0)
        self.logger.info("loop")

    @asyncio.coroutine
    def teardown(self):
        yield from asyncio.sleep(0.0)
        self.logger.info("teardown")
