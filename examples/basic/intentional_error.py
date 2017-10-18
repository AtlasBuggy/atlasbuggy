import asyncio
from atlasbuggy import Orchestrator, Node, run


class BasicOrchestrator(Orchestrator):
    def __init__(self, event_loop):
        super(BasicOrchestrator, self).__init__(event_loop, self.make_logger(10, write=False))

        self.test_node = BasicNode()
        self.add_nodes(self.test_node)

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
            # intentional error:
            counter = 1 / counter

            self.logger.info("node counter: %s" % counter)
            await asyncio.sleep(1.0)
            counter += 1


run(BasicOrchestrator)
