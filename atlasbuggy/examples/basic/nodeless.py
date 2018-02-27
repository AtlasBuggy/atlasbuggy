import asyncio
from atlasbuggy import Orchestrator


class BasicOrchestrator(Orchestrator):
    def __init__(self, event_loop):
        super(BasicOrchestrator, self).__init__(event_loop, )

    async def loop(self):
        counter = 0
        while True:
            self.logger.info("counter: %s" % counter)
            await asyncio.sleep(0.5)
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

    loop.close()


main()
