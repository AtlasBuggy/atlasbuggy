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

    @asyncio.coroutine
    def _run(self):
        """
        Added async tag since this method will be asynchronous. Make sure to include this tag
        when subclassing AsyncStream
        """
        try:
            self.started()
            yield from self.run()
        except KeyboardInterrupt:
            # don't print exception
            self.logger.debug("KeyboardInterrupt")
        except asyncio.CancelledError:
            # don't print exception
            self.logger.debug("CancelledError")
        except BaseException as error:
            self.logger.debug("Catching exception")
            self.logger.exception(error)
        finally:
            self.logger.debug("run finished")
            self.exit()
            self._stop()

    @asyncio.coroutine
    def update(self):
        return asyncio.sleep(0.0)

    @asyncio.coroutine
    def run(self):
        """
        Added async tag since this method will be asynchronous
        """
        yield from asyncio.sleep(0.0)

    @asyncio.coroutine
    def post(self, data, service="default", **kwargs):
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
                    yield from subscription.async_post(post_fn(data), **kwargs)
        yield from asyncio.sleep(0.0)
