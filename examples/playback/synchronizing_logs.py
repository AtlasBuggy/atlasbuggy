
from atlasbuggy.log.playback import PlaybackNode

from atlasbuggy.examples.subscriptions.multiple_producers import *


class FastSensorPlayback(PlaybackNode):
    def __init__(self, enabled=True):
        super(FastSensorPlayback, self).__init__(
            "../subscriptions/logs/multiple_producers_demo/FastSensor/multiple_producers_demo.log",
            enabled=enabled)

    async def parse(self, line):
        message = FastSensorMessage.parse(line.message)
        # self.logger.warning("fast time: %s" % self.current_time())
        if message is not None:
            self.logger.info("recovered: %s" % message)
            await self.broadcast(message)
        else:
            await asyncio.sleep(0.0)


class SlowSensorPlayback(PlaybackNode):
    def __init__(self, enabled=True):
        super(SlowSensorPlayback, self).__init__(
            "../subscriptions/logs/multiple_producers_demo/SlowSensor/multiple_producers_demo.log",
            enabled=enabled)

    async def parse(self, line):
        message = SlowSensorMessage.parse(line.message)
        # self.logger.warning("\tslow time: %s" % self.current_time())
        if message is not None:
            self.logger.info("recovered: %s" % message)
            await self.broadcast(message)
        else:
            await asyncio.sleep(0.0)


class PlaybackOrchestrator(Orchestrator):
    def __init__(self, event_loop):
        self.set_default(write=False)

        super(PlaybackOrchestrator, self).__init__(event_loop)

        fast_sensor = FastSensorPlayback()
        slow_sensor = SlowSensorPlayback()
        algorithm = AlgorithmNode()

        self.add_nodes(fast_sensor, slow_sensor, algorithm)

        self.subscribe(algorithm.fast_sensor_tag, fast_sensor, algorithm)
        self.subscribe(algorithm.slow_sensor_tag, slow_sensor, algorithm)

        self.t0 = 0
        self.t1 = 0

    async def setup(self):
        self.t0 = time.time()

    async def teardown(self):
        self.t1 = time.time()

        print("took: %ss" % (self.t1 - self.t0))

run(PlaybackOrchestrator)
