import asyncio
import unittest

from node import Node
from orchestrator import Orchestrator


class BasicOrchestrator(Orchestrator):
    def __init__(self, event_loop):
        super(BasicOrchestrator, self).__init__(event_loop)

    async def loop(self):
        counter = 0
        while True:
            print("counter:", counter)
            await asyncio.sleep(1.0)
            counter += 1


class TestNode(Node):
    def __init__(self):
        super(TestNode, self).__init__()

    async def loop(self):
        counter = 0
        while True:
            print("node counter:", counter)
            await asyncio.sleep(1.0)
            counter += 1


async def delayed_stop(seconds):
    await asyncio.sleep(seconds)
    raise KeyboardInterrupt


class TestOrchestrator(unittest.TestCase):
    def test_nodeless_shutdown(self):
        loop = asyncio.get_event_loop()
        orchestrator = BasicOrchestrator(loop)

        asyncio.ensure_future(delayed_stop(2))
        try:
            loop.run_until_complete(orchestrator.run())
        except KeyboardInterrupt:
            print("Interrupted")

    def test_standard_shutdown(self):
        loop = asyncio.get_event_loop()
        orchestrator = BasicOrchestrator(loop)
        test_node = TestNode()

        asyncio.ensure_future(delayed_stop(2))
        orchestrator.add_nodes(test_node)

        try:
            loop.run_until_complete(orchestrator.run())
        except KeyboardInterrupt:
            print("Interrupted")


if __name__ == '__main__':
    unittest.main()
