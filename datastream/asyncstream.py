from atlasbuggy.datastream import DataStream


class AsyncStream(DataStream):
    def __init__(self, enabled, name=None, log_level=None, version="1.0"):
        """
        Initialization for asynchronous stream
        """
        super(AsyncStream, self).__init__(enabled, name, log_level, version)

        self.task = None
        self.coroutine = None

    async def _run(self):
        """
        Added async tag since this method will be asynchronous
        """

        try:
            await self.run()
        except BaseException:
            self._stop()
            self.logger.debug("catching exception in async loop")
            self.exit()
            raise

        self.logger.debug("run finished")
        self._stop()
        self.exit()

    async def run(self):
        """
        Added async tag since this method will be asynchronous
        """
        pass