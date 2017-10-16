import asyncio
import logging

class Node:
    def __init__(self, enabled=True, level=None, name=None, writelog=True):
        self.enabled = enabled
        self.level = logging.WARNING if level is None else level
        self.name = Node.__class__.__name__ if name is None else name
        self.writelog = writelog

    @asyncio.coroutine
    def setup(self):
        print("something")

    @asyncio.coroutine
    def loop(self):
        pass

    @asyncio.coroutine
    def teardown(self):
        pass
