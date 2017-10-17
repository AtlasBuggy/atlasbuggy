import signal
import logging
from log_factory import make_logger
import asyncio


class Orchestrator:
    def __init__(self, event_loop, logger=None, name=None):
        self.event_loop = event_loop
        self.name = self.__class__.__name__ if name is None else name
        if logger is None:
            self.logger = make_logger(self.name, logging.DEBUG)

        self.nodes = []
        self.loop_tasks = []
        self.halt_called = False

        self.event_loop.add_signal_handler(signal.SIGINT, self._stop_callback, self.event_loop)

    def add_nodes(self, *nodes):
        """Add the tasks associated with each node to the event loop"""
        for node in nodes:
            if node.enabled:
                self.nodes.append(node)

    @asyncio.coroutine
    def setup(self):
        self.logger.info("setup")

    @asyncio.coroutine
    def loop(self):
        self.logger.info("loop")

    @asyncio.coroutine
    def teardown(self):
        self.logger.info("teardown")

    def halt(self):
        if self.halt_called:
            self.logger.info("already halted")
            return

        self.halt_called = True
        self.logger.info("halting")
        self._stop_callback(self.event_loop)
        if len(self.nodes) > 0:
            teardown_tasks = [asyncio.ensure_future(self.teardown())]
            for node in self.nodes:
                teardown_tasks.append(asyncio.ensure_future(node.teardown()))

            return asyncio.wait(teardown_tasks)
        else:
            return asyncio.sleep(0.0)

    def run(self):
        """First call each node's startup task then return the collected node coroutines to run indefinitely"""
        setup_tasks = [asyncio.ensure_future(self.setup())]
        self.halt_called = False
        for node in self.nodes:
            setup_tasks.append(asyncio.ensure_future(node.setup()))
        self.event_loop.run_until_complete(asyncio.wait(setup_tasks))

        self.loop_tasks.append(asyncio.ensure_future(self.loop()))
        for node in self.nodes:
            self.loop_tasks.append(asyncio.ensure_future(node.loop()))

        return asyncio.wait(self.loop_tasks, return_when=asyncio.FIRST_COMPLETED)

    def _stop_callback(self, loop):
        for task in self.loop_tasks:
            result = task.cancel()
            self.logger.info("Cancelling %s: %s" % (task, result))
