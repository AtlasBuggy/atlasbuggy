import re

from atlasbuggy.log.playback import PlaybackNode

try:
    from examples.subscriptions.multiple_producers import *
except ImportError:
    from ..subscriptions.multiple_producers import *


class FastSensorPlayback(PlaybackNode):
    def __init__(self, enabled=True):
        super(FastSensorPlayback, self).__init__(
            "../subscriptions/logs/multiple_producers_demo/FastSensor/multiple_producers_demo.log",
            enabled=enabled)

    async def parse(self, line):
        message = FastSensorMessage.parse(line.message)
        self.logger.warning("relative time: %s" % self.current_time())
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
        self.logger.warning("relative time: %s" % self.current_time())
        if message is not None:
            self.logger.info("recovered: %s" % message)
            await self.broadcast(message)
        else:
            await asyncio.sleep(0.0)


class PlaybackOrchestrator(Orchestrator):
    def __init__(self, event_loop):
        self.set_default(write=False, level=30)

        super(PlaybackOrchestrator, self).__init__(event_loop)

        fast_sensor = FastSensorPlayback()
        slow_sensor = SlowSensorPlayback()
        algorithm = AlgorithmNode()

        self.add_nodes(fast_sensor, slow_sensor, algorithm)

        self.subscribe(algorithm.fast_sensor_tag, fast_sensor, algorithm)
        self.subscribe(algorithm.slow_sensor_tag, slow_sensor, algorithm)


run_orchestrator(PlaybackOrchestrator)
