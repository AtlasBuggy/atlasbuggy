# Feed Subscriptions

In many ways this example is simplier that the "simple" example. In this example, we will implement a true producer-consumer model by making use of atlasbuggy's Feed subscription type.

Here our producer is simply a counter that increments every 0.5 seconds:

```python
class Producer(AsyncStream):
    """This stream produces content"""

    def __init__(self):
        self.counter = 0  # shared resource
        super(Producer, self).__init__(log_level=20)

    async def run(self):
        while self.is_running():
            await asyncio.sleep(0.5)  # wait 0.5 seconds
            self.logger.info("I'm producing '%s'" % self.counter)  # signal that counter was posted
            self.counter += 1  # change the value
```
