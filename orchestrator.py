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

    def teardown(self):
        self.logger.info("teardown")
        self._stop_callback(self.event_loop)
        if len(self.nodes) > 0:
            teardown_tasks = []
            for node in self.nodes:
                teardown_tasks.append(asyncio.async(node.teardown()))

            return asyncio.wait(teardown_tasks)
        else:
            return asyncio.sleep(0.0)

    def run(self):
        """First call each node's startup task then return the collected node coroutines to run indefinitely"""
        setup_tasks = [asyncio.async(self.setup())]
        for node in self.nodes:
            setup_tasks.append(asyncio.async(node.setup()))
        self.event_loop.run_until_complete(asyncio.wait(setup_tasks))

        self.loop_tasks.append(asyncio.async(self.loop()))
        for node in self.nodes:
            setup_tasks.append(asyncio.async(node.loop()))

        return asyncio.wait(self.loop_tasks, return_when=asyncio.FIRST_COMPLETED)

    def _stop_callback(self, loop):
        for task in self.loop_tasks:
            result = task.cancel()
            self.logger.info("Cancelling %s: %s" % (task, result))


if __name__ == '__main__':
    async def delayed_stop(seconds):
        await asyncio.sleep(seconds)
        raise KeyboardInterrupt


    def test():
        loop = asyncio.get_event_loop()
        orchestrator = Orchestrator(loop)
        asyncio.ensure_future(delayed_stop(4))

        try:
            loop.run_until_complete(orchestrator.run())
        except KeyboardInterrupt:
            print("Interrupted")
        finally:
            loop.run_until_complete(orchestrator.teardown())


    test()
