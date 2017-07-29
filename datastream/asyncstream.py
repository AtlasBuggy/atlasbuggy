import asyncio
from ..datastream import DataStream


class AsyncStream(DataStream):
    def __init__(self, enabled=True, log_level=None, name=None):
        """
        Initialization for asynchronous stream
        """
        super(AsyncStream, self).__init__(enabled, log_level, name)

        self.task = None
        self.coroutine = None

    def _subscribed(self, subscription):
        subscription.is_async = True  # tell subscription to use the async queue

    async def _run(self):
        """
        Added async tag since this method will be asynchronous. Make sure to include this tag
        when subclassing AsyncStream
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
        """
        Post data to subscribed consumer streams using the async method
        
        :param data: Data to post 
        :param service: which service to post data to
        """
        if service in self.subscribers:
            for subscription in self.subscribers[service]:
                if subscription.enabled:
                    assert service == subscription.service
                    post_fn = self.subscription_services[service]
                    await subscription.async_post(post_fn(data))
        await asyncio.sleep(0.0)
