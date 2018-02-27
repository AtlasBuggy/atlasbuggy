import asyncio
from atlasbuggy import Orchestrator, Node, run


class SpawnerNode(Node):
    def __init__(self, enabled=True):
        self.tasks = []
        super(SpawnerNode, self).__init__(enabled)

    async def loop(self):
        task_num = 0
        self.tasks = []
        while True:
            task = asyncio.ensure_future(self.extra_task(task_num), loop=self.event_loop)
            self.tasks.append(task)
            task_num += 1

            for task in self.tasks:
                self.check_task(task)

            await asyncio.sleep(0.15)

    async def extra_task(self, task_num):
        self.logger.info("Task #%s stage 1" % task_num)
        await asyncio.sleep(0.15)
        self.logger.info("Task #%s stage 2" % task_num)
        await asyncio.sleep(0.15)
        self.logger.info("Task #%s stage 3" % task_num)

    async def teardown(self):
        for task in self.tasks:
            self.cancel_task(task)

    def cancel_task(self, task):
        task.cancel()
        self.check_task(task)

    def check_task(self, task):
        if task.cancelled():
            self.logger.debug("Task '%s' was cancelled" % task)
        elif task.done() and task.exception() is not None:
            raise task.exception()


class MyOrchestrator(Orchestrator):
    def __init__(self, event_loop):
        super(MyOrchestrator, self).__init__(event_loop)

        node = SpawnerNode()
        self.add_nodes(node)


run(MyOrchestrator)
