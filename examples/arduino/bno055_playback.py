import asyncio

from atlasbuggy import Orchestrator, run
from atlasbuggy.log.playback import PlaybackNode

try:
    from .bno055 import Bno055Message, ConsumerNode
except ModuleNotFoundError:
    from atlasbuggy.examples.arduino.bno055 import Bno055Message, ConsumerNode


class BNO055Playback(PlaybackNode):
    def __init__(self, enabled=True):
        super(BNO055Playback, self).__init__(
            "logs/bno055_demo/BNO055/bno055_demo.log",
            enabled=enabled)

    async def parse(self, line):
        message = Bno055Message.parse(line.message)
        if message is not None:
            # self.logger.info("recovered: %s" % message)
            print(message.euler.get_tuple())
            await self.broadcast(message)
        else:
            self.logger.info(line.full)
            await asyncio.sleep(0.0)


class MyOrchestrator(Orchestrator):
    def __init__(self, event_loop):
        super(MyOrchestrator, self).__init__(event_loop)

        bno055 = BNO055Playback()
        consumer = ConsumerNode()

        self.add_nodes(bno055, consumer)
        self.subscribe(consumer.producer_tag, bno055, consumer)


if __name__ == '__main__':
    run(MyOrchestrator)
