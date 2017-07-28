from threading import Thread

from ..datastream import DataStream


class ThreadedStream(DataStream):
    def __init__(self, enabled=True, log_level=None, name=None):
        """
        Initialization for threaded stream
        """
        super(ThreadedStream, self).__init__(enabled, log_level, name)

        self.thread = Thread(target=self._run)
        self.thread.daemon = False

    def set_to_daemon(self):
        """
        Set this thread to exit when the main thread exits instead of relying on the exit events
        """
        self.thread.daemon = True
        self.logger.debug("thread is now daemon")

    def join(self):
        """
        Wait for thread to finish
        """
        self.thread.join()

    def _subscribed(self, subscription):
        subscription.is_async = False  # tell subscription to use the sync queue

    def _init(self):
        """
        Start the thread
        """
        self.thread.start()

    def post(self, data, service="default"):
        """
        Post data to subscribed consumer streams using the sync method

        :param data: Data to post 
        :param service: which service to post data to
        """
        if service in self.subscribers:
            for subscription in self.subscribers[service]:
                if subscription.enabled:
                    assert service == subscription.service
                    post_fn = self.subscription_services[service]
                    subscription.sync_post(post_fn(data))
