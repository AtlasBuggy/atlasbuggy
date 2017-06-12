import time
import logging
from threading import Thread, Event


class DataStream:
    _exit_events = []
    _log_info = {}

    def __init__(self, enabled, name=None, log_level=None):
        """
        Initialization. No streams have started yet.
        :param enabled: True or False
        :param name: Name to show in the logger output. Class name by default
        """
        if name is None:
            name = self.__class__.__name__
        if log_level is None:
            log_level = logging.INFO

        self.name = name
        self.enabled = enabled

        self.timestamp = None
        self.start_time = None

        self.started = Event()
        self.closed = Event()
        self.exited = Event()
        DataStream._exit_events.append(self.exited)

        self.streams = {}

        self.logger = logging.getLogger(self.name)
        if len(DataStream._log_info) == 0:
            raise ValueError("Declare Robot before initializing any streams.")
        if DataStream._log_info["log_level"] < log_level:
            self.log_level = DataStream._log_info["log_level"]
        else:
            self.log_level = log_level
        self.logger.setLevel(logging.DEBUG)  # catch all logs

        self.print_handle = logging.StreamHandler()
        self.print_handle.setLevel(self.log_level)  # only print what user specifies
        formatter = logging.Formatter(self._log_info["format"])
        self.print_handle.setFormatter(formatter)
        self.logger.addHandler(self.print_handle)

        if DataStream._log_info["file_handle"] is not None:
            self.logger.addHandler(DataStream._log_info["file_handle"])

    def dt(self, current_time=None, use_current_time=True):
        """
        Time since stream_start was called. Supply your own timestamp or use the current system time
        Overwrite time_started to change the initial time
        :return:
        """
        if current_time is None and use_current_time:
            current_time = time.time()
        self.timestamp = current_time

        if self.start_time is None or self.timestamp is None:
            return 0.0
        else:
            return self.timestamp - self.start_time

    def give(self, **streams):
        """
        Share an instance of another stream. Should be called before start
        :param streams: keyword arguments of all streams being shared
        :return:
        """
        self.streams = streams
        self.take()
        self.logger.debug("receiving streams:" + str([str(stream) for stream in streams.values()]))

    def receive_log(self, message, line_info):
        pass

    def take(self):
        """
        Callback for give. Called before start
        :return:
        """
        pass

    def start(self):
        """
        Callback for stream_start. Time has started, run has not been called.
        :return:
        """
        pass

    @staticmethod
    def all_running():
        """
        Check if all exit events are False
        :return: False when all streams have called self.exit
          All streams have exited when:
            - their run methods have completed
            - when Robot catches a KeyboardInterrupt or an asyncio.CancelledError
            - DataStream.exit_all() is called
            - All streams have called self.exit themselves
        """
        return not all([result.is_set() for result in DataStream._exit_events])

    @staticmethod
    def any_stopped():
        """
        Check if all exit events are False
        :return: False when all streams have called self.exit
          All streams have exited when:
            - their run methods have completed
            - when Robot catches a KeyboardInterrupt or an asyncio.CancelledError
            - DataStream.exit_all() is called
            - All streams have called self.exit themselves
        """
        return any([result.is_set() for result in DataStream._exit_events])

    def running(self):
        """
        Check if stream is running. Use this in your while loops in your run methods
        """
        return not self.exited.is_set()

    def time_started(self):
        """
        Behavior for starting the timer.
        :return: What the initial time should be
        """
        return time.time()

    def _init(self):
        """
        Extra startup behavior
        """

    def _start(self):
        """
        Wrapper for starting the stream
        :return:
        """
        if not self.started.is_set():
            if not self.enabled:
                self.logger.debug("stream not enabled")
                return

            self.logger.debug("starting")
            self.started.set()
            self.start_time = self.time_started()
            self.start()
            self._init()

    def _run(self):
        """
        Wrapper for running stream. Doesn't use self.enabled since Robot handles disabled streams
        """
        pass

    def run(self):
        """
        Main behavior of the stream. Put 'while self.running():' in this method
        """
        pass

    def update(self):
        """
        Optional method to be called inside run's while loop
        """
        pass

    def _close(self):
        """
        Wrapper for closing the stream. Assumes that exit has been set
        """
        if not self.enabled:
            return
        if not self.closed.is_set():
            self.closed.set()
            self.close()
            self.logger.debug("closed")
            # if DataStream.log_info["write"]:
            #     self.logger.removeHandler(DataStream.log_info["file_handle"])
            # self.logger.removeHandler(self.print_handle)

    def close(self):
        """
        Close behavior of the stream
        """
        pass

    def exit(self):
        """
        Signal for this stream to exit
        """
        self.exited.set()

    @staticmethod
    def exit_all():
        """
        Signal for all streams to exit
        """
        for event in DataStream._exit_events:
            event.set()

    def __str__(self):
        return self.name

    def __repr__(self):
        return "<%s, enabled=%s>" % (self.__class__.__name__, self.enabled)


class ThreadedStream(DataStream):
    def __init__(self, enabled, name=None, log_level=None):
        """
        Initialization for threaded stream
        """
        super(ThreadedStream, self).__init__(enabled, name, log_level)

        self.thread = Thread(target=self.run)
        self.thread.daemon = False

    def set_to_daemon(self):
        """
        Set this thread to exit when the main thread exits instead of relying on the exit events
        """
        self.thread.daemon = True
        self.logger.debug("thread is now daemon")

    def _run(self):
        self.run()
        self.logger.debug("run finished")
        self.exit()

    def _init(self):
        """
        Start the thread
        """
        self.thread.start()

    def __repr__(self):
        return "<%s, enabled=%s, threaded>" % (self.__class__.__name__, self.enabled)


class AsyncStream(DataStream):
    def __init__(self, enabled, name=None, log_level=None):
        """
        Initialization for asynchronous stream
        """
        super(AsyncStream, self).__init__(enabled, name, log_level)

        self.asyncio_loop = None
        self.task = None
        self.coroutine = None

    async def _run(self):
        """
        Added async tag since this method will be asynchronous
        """
        await self.run()
        self.logger.debug("run finished")
        self.exit()

    async def run(self):
        """
        Added async tag since this method will be asynchronous
        """
        pass

    def __repr__(self):
        return "<%s, enabled=%s, asynchronous>" % (self.__class__.__name__, self.enabled)
