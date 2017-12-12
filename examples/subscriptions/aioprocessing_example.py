import math
import time
import asyncio
import aioprocessing

from atlasbuggy import Node, Orchestrator, run


def primes(n):
    if n == 2:
        return [2]
    elif n < 2:
        return []
    s = list(range(3, n + 1, 2))
    mroot = math.sqrt(n)
    half = (n + 1) // 2 - 1
    i = 0
    m = 3
    while m <= mroot:
        if s[i]:
            j = (m * m - 3) // 2
            s[j] = 0
            while j < half:
                s[j] = 0
                j += m
        i = i + 1
        m = 2 * i + 3

    return [2] + [x for x in s if x]


class ProcessingQueueNode(Node):
    def __init__(self, enabled=True):
        super(ProcessingQueueNode, self).__init__(enabled)
        self.process = aioprocessing.AioProcess(target=self.processor_heavy_fn)
        self.read_queue = aioprocessing.AioQueue()
        self.write_queue = aioprocessing.AioQueue()
        self.lock = aioprocessing.AioLock()
        self.exit_event = aioprocessing.AioEvent()

    async def setup(self):
        self.process.start()

    def processor_heavy_fn(self):
        while True:
            if self.exit_event.is_set():
                return

            with self.lock:
                results = []
                if not self.write_queue.empty():
                    while not self.write_queue.empty():
                        if self.exit_event.is_set():
                            return

                        n = self.write_queue.get()
                        results.append(primes(n))

                    self.read_queue.put(results)
                else:
                    time.sleep(0.01)

    async def loop(self):
        ns = [5, 10, 25, 255, 1000]
        while True:
            for n in ns:
                await self.write_queue.coro_put(n)

            if not self.read_queue.empty():
                while not self.read_queue.empty():
                    with self.lock:
                        results = await self.read_queue.coro_get()
                        print(results)
            else:
                await asyncio.sleep(0.0)

    async def teardown(self):
        self.exit_event.set()


class MyOrchestrator(Orchestrator):
    def __init__(self, event_loop):
        super(MyOrchestrator, self).__init__(event_loop)

        self.processing_queue = ProcessingQueueNode()

        self.add_nodes(self.processing_queue)


run(MyOrchestrator)
