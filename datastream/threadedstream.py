from threading import Thread

from atlasbuggy.datastream import DataStream


class ThreadedStream(DataStream):
    def __init__(self, enabled, name=None, log_level=None, version="1.0"):
        """
        Initialization for threaded stream
        """
        super(ThreadedStream, self).__init__(enabled, name, log_level, version)

        self.thread = Thread(target=self._run)
        self.thread.daemon = False

    def set_to_daemon(self):
        """
        Set this thread to exit when the main thread exits instead of relying on the exit events
        """
        self.thread.daemon = True
        self.logger.debug("thread is now daemon")

    def join(self):
        self.thread.join()

    def _init(self):
        """
        Start the thread
        """
        self.thread.start()