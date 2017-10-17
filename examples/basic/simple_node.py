import asyncio
from atlasbuggy import Orchestrator, Node


class BasicOrchestrator(Orchestrator):
    def __init__(self, event_loop):
        super(BasicOrchestrator, self).__init__(event_loop)

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
            self.logger.info("node counter: %s" % counter)
            await asyncio.sleep(1.0)
            counter += 1


def main():
    loop = asyncio.get_event_loop()
    orchestrator = BasicOrchestrator(loop)

    try:
        loop.run_until_complete(orchestrator.run())
    except KeyboardInterrupt:
        print("Interrupted")
    finally:
        loop.run_until_complete(orchestrator.halt())

main()
