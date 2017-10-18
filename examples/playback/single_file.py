import re

from atlasbuggy.log.playback import PlaybackNode

try:
    from examples.subscriptions.converted_messages import *
except ImportError:
    from ..subscriptions.converted_messages import *


class ImmutableProducerPlayback(PlaybackNode):
    def __init__(self, enabled=True):
        super(ImmutableProducerPlayback, self).__init__(
            "../subscriptions/logs/converted_messages_demo/ImmutableProducer/converted_messages_demo.log",
            enabled=enabled, logger=self.make_logger(level=30))

        self.message_regex = r"sending: ProducerMessage\(t=(\d.*), x=(\d.*), y=(\d.*), z=(\d.*)\)"

    async def parse(self, line):
        match = re.match(self.message_regex, line.message)
        if match is not None:
            message_time = float(match.group(1))
            x = float(match.group(2))
            y = float(match.group(3))
            z = float(match.group(4))

            message = ProducerMessage(message_time, x, y, z)
            self.logger.info("recovered: %s" % message)
            await self.broadcast(message)
        else:
            await asyncio.sleep(0.0)


def message_converter(message: ProducerMessage):
    return ConsumerMessage(message.timestamp, message.x, message.y + message.z)


class PlaybackOrchestrator(Orchestrator):
    def __init__(self, event_loop):
        self.set_default(write=False)

        super(PlaybackOrchestrator, self).__init__(event_loop)

        producer = ImmutableProducerPlayback()
        consumer = ImmutableConsumer()

        self.add_nodes(producer, consumer)
        self.subscribe(consumer.producer_tag, producer, consumer, message_converter=message_converter)


run_orchestrator(PlaybackOrchestrator)
