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
            self.logger.info("counter: %s" % counter)
            await asyncio.sleep(1.0)
            counter += 1


class BasicNode(Node):
    def __init__(self):
        super(BasicNode, self).__init__()

    async def loop(self):
        counter = 0
        while True:
            self.logger.info("node counter: %s" % counter)
            await asyncio.sleep(1.0)
            counter += 1


class TestNode1(Node):
    def __init__(self):
        super(TestNode1, self).__init__()

    async def loop(self):
        counter = 0
        while True:
            self.logger.info("node counter: %s" % counter)
            await asyncio.sleep(1.0)
            counter += 1


class TestNode2(Node):
    def __init__(self):
        super(TestNode2, self).__init__()

    async def loop(self):
        counter = 0
        while True:
            self.logger.info("node counter: %s" % counter)
            await asyncio.sleep(0.5)
            counter += 2


class TestNode3(Node):
    def __init__(self):
        super(TestNode3, self).__init__()

    async def loop(self):
        counter = 0
        while True:
            self.logger.info("node counter: %s" % counter)
            await asyncio.sleep(0.25)
            counter += 4


class MultiNodeOrchestrator(Orchestrator):
    def __init__(self, event_loop):
        super(MultiNodeOrchestrator, self).__init__(event_loop)

        self.node1 = TestNode1()
        self.node2 = TestNode2()
        self.node3 = TestNode3()

        self.add_nodes(self.node1, self.node2, self.node3)

    async def loop(self):
        counter = 0
        while True:
            self.logger.info("orchestrator counter: %s" % counter)
            await asyncio.sleep(2.0)
            counter += 1

            if counter > 3:
                self.logger.info("counter = 4. Shutting down")
                self.halt()
                return


async def delayed_stop(seconds):
    await asyncio.sleep(seconds)
    raise KeyboardInterrupt


class TestOrchestrator(unittest.TestCase):
    def test_nodeless_shutdown(self):
        print("\n----- test_nodeless_shutdown -----")
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        orchestrator = BasicOrchestrator(loop)

        asyncio.ensure_future(delayed_stop(2))
        try:
            loop.run_until_complete(orchestrator.run())
        except KeyboardInterrupt:
            print("Interrupted")
        finally:
            loop.run_until_complete(orchestrator.halt())

        loop.close()

    def test_standard_shutdown(self):
        print("\n----- test_standard_shutdown -----")
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        orchestrator = BasicOrchestrator(loop)
        test_node = BasicNode()

        asyncio.ensure_future(delayed_stop(2))
        orchestrator.add_nodes(test_node)

        try:
            loop.run_until_complete(orchestrator.run())
        except KeyboardInterrupt:
            print("Interrupted")
        finally:
            loop.run_until_complete(orchestrator.halt())

        loop.close()

    def test_multinode_controlled_stop(self):
        print("\n----- test_multinode_controlled_stop -----")

        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        orchestrator = MultiNodeOrchestrator(loop)

        try:
            loop.run_until_complete(orchestrator.run())
        except KeyboardInterrupt:
            print("Interrupted")
        finally:
            loop.run_until_complete(orchestrator.halt())

        loop.close()


if __name__ == '__main__':
    unittest.main()
