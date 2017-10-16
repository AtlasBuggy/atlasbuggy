import signal
import asyncio


class Orchestrator:
    def __init__(self, event_loop):
        self.event_loop = event_loop
        self.setup_tasks = [asyncio.async(self.setup())]
        self.loop_tasks = [asyncio.async(self.loop())]
        self.teardown_tasks = [asyncio.async(self.teardown())]

        self.event_loop.add_signal_handler(signal.SIGINT, self._stop_callback, self.event_loop)

    def add_nodes(self, *nodes):
        """Add the tasks associated with each node to the event loop"""
        for node in nodes:
            if node.enabled:
                self.setup_tasks.append(asyncio.async(node.setup()))
                self.loop_tasks.append(asyncio.async(node.loop()))
                self.teardown_tasks.append(asyncio.async(node.teardown()))

    @asyncio.coroutine
    def setup(self):
        print("something")

    @asyncio.coroutine
    def loop(self):
        pass

    @asyncio.coroutine
    def teardown(self):
        pass

    def run(self):
        """First call each node's startup task then return the collected node coroutines to run indefinitely"""
        self.event_loop.run_until_complete(asyncio.gather(*self.setup_tasks))

        return asyncio.wait(self.loop_tasks, return_when=asyncio.FIRST_COMPLETED)

    def _stop_callback(self, loop):
        for task in self.loop_tasks:
            result = task.cancel()
            print("Cancelling %s: %s" % (task, result))
