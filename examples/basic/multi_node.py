import asyncio
from atlasbuggy import Orchestrator, Node, run_orchestrator


class Node1(Node):
    def __init__(self):
        super(Node1, self).__init__()

    async def loop(self):
        counter = 0
        while True:
            self.logger.info("node counter: %s" % counter)
            await asyncio.sleep(1.0)
            counter += 1


class Node2(Node):
    def __init__(self):
        super(Node2, self).__init__()

    async def loop(self):
        counter = 0
        while True:
            self.logger.info("node counter: %s" % counter)
            await asyncio.sleep(0.5)
            counter += 2


class Node3(Node):
    def __init__(self):
        super(Node3, self).__init__()

    async def loop(self):
        counter = 0
        while True:
            self.logger.info("node counter: %s" % counter)
            await asyncio.sleep(0.25)
            counter += 4


class MultiNodeOrchestrator(Orchestrator):
    def __init__(self, event_loop):
        super(MultiNodeOrchestrator, self).__init__(event_loop)

        self.node1 = Node1()
        self.node2 = Node2()
        self.node3 = Node3()

        self.add_nodes(self.node1, self.node2, self.node3)

    async def loop(self):
        counter = 0
        while True:
            self.logger.info("orchestrator counter: %s" % counter)
            await asyncio.sleep(0.5)
            counter += 1

            if counter > 3:
                self.logger.info("counter = 4. Shutting down")
                # self.halt()  # halting or returning are valid options
                return

run_orchestrator(MultiNodeOrchestrator)
