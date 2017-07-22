import asyncio
from atlasbuggy.datastream import DataStream


class AsyncStream(DataStream):
    def __init__(self, enabled, name=None, log_level=None):
        """
        Initialization for asynchronous stream
        """
        super(AsyncStream, self).__init__(enabled, name, log_level)

        self.task = None
        self.coroutine = None

    async def _run(self):
        """
        Added async tag since this method will be asynchronous
        """

        try:
            self.started()
            await self.run()
        except BaseException:
            self._stop()
            self.logger.debug("catching exception in async loop")
            self.exit()
            raise

        self.logger.debug("run finished")
        self._stop()
        self.exit()

    async def update(self):
        return asyncio.sleep(0.0)

    async def run(self):
        """
        Added async tag since this method will be asynchronous
        """
        pass

    async def post(self, data, service="default"):
        if service in self.subscribers:
            for subscription in self.subscribers[service]:
                if subscription.enabled:
                    assert service == subscription.service
                    post_fn = self.subscription_services[service]
                    await subscription.async_post(post_fn(data))
