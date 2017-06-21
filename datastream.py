import time
import logging
from threading import Thread, Event


class DataStream:
    _exited = Event()  # signal to exit
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
        if type(self.name) != str:
            raise ValueError("Name isn't a string: %s" % self.name)

        self.enabled = enabled

        self.timestamp = None  # current time since epoch
        self.start_time = None  # stream start time. Can be set externally

        self._has_started = Event()  # self._start flag
        self._has_stopped = Event()  # self._stop flag

        self.streams = {}  # other streams this one has access to. (Call the give method)

        # instance of logging. Use this instance to print debug statement and log
        self.logger = logging.getLogger(self.name)

        # make sure robot has instantiated the log info before this stream
        if len(DataStream._log_info) == 0:
            raise ValueError("Declare Robot before initializing any streams.")
        if DataStream._log_info["log_level"] < log_level:  # robot's log level takes priority over individual streams
            self.log_level = DataStream._log_info["log_level"]
        else:
            self.log_level = log_level
        self.logger.setLevel(logging.DEBUG)  # catch all logs

        self.print_handle = logging.StreamHandler()  # initialize log printing
        self.print_handle.setLevel(self.log_level)  # only print what user specifies

        # define how logs are formatted based on how they were defined in Robot
        formatter = logging.Formatter(self._log_info["format"])
        self.print_handle.setFormatter(formatter)
        self.logger.addHandler(self.print_handle)

        # add file logging if Robot has enabled it
        if DataStream._log_info["file_handle"] is not None:
            self.logger.addHandler(DataStream._log_info["file_handle"])

    def dt(self, current_time=None, use_current_time=True):
        """
        Time since stream_start was called. Supply your own timestamp or use the current system time
        Overwrite time_started to change the initial time
        :return:
        """
        # use the system time as current time by default. If you have another time source (e.g. log files),
        # use this method to update the stream's time
        if current_time is None and use_current_time:
            current_time = time.time()
        self.timestamp = current_time

        if self.start_time is None or self.timestamp is None:
            return 0.0
        else:
            return self.timestamp - self.start_time

    def give(self, **streams):
        """
        Share an instance of another stream. Should be called before start (before Robot.run)
        :param streams: keyword arguments of all streams being shared
        :return:
        """
        self.streams = streams
        self.take()
        self.logger.debug("receiving streams:" + str([str(stream) for stream in streams.values()]))

    def receive_log(self, log_level, message, line_info):
        """
        If LogParser is given to Robot and this stream is given to LogParser, it will give any matching log messages it
        finds in a log file. This includes error messages

        :param log_level: type of log message
        :param message: string found in the log file
        :param line_info: a dictionary of information discovered. Keys in the dictionary:
            timestamp, year, month, day, hour, minute, second, millisecond,
            name - name of the stream that produced the message,
            message, linenumber, filename, loglevel
        :return:
        """
        pass

    def take(self):
        """
        Callback for give

        Usage:
        new_stream = SomeStream()
        other_stream = OtherStream()

        new_stream.give(identifying_string=other_stream)  # new_stream's take is called

        Example (overwrite this method and put this code in):

        self.other_stream = self.streams["identifying_string"]
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
    def running():
        """
        Check if stream is running. Use this in your while loops in your run methods:

        while self.running():
            ...
        :return:
        """
        return not DataStream._exited.is_set()

    def time_started(self):
        """
        Behavior for starting the timer.
        :return: What the initial time should be (None is acceptable. Set self.start_time later)
        """
        return time.time()

    def _init(self):
        """
        Internal extra startup behavior
        """

    def _start(self):
        """
        Wrapper for starting the stream
        :return:
        """
        if not self._has_started.is_set():  # only call _start once
            if not self.enabled:
                self.logger.debug("stream not enabled")
                return

            self.logger.debug("starting")
            self._has_started.set()
            self.start_time = self.time_started()
            self.start()
            self._init()

    def _run(self):
        """
        Wrapper for running stream
        """

        try:
            self.run()
        except BaseException:
            self.stop()  # in threads, stop is called inside the thread instead to avoid race conditions
            self.logger.debug("catching exception in threaded loop")
            self.exit()
            raise

        self.logger.debug("run finished")
        self.stop()
        self.exit()

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

    def _stop(self):
        """
        Wrapper for stopping the stream. Assumes that exit has been set
        """
        if not self.enabled:
            return
        if not self._has_stopped.is_set():  # only call _stop once
            self._has_stopped.set()
            self.logger.debug("stopping")
            self.stop()
            self.logger.debug("closed")

    def stop(self):
        """
        Stop behavior of the stream
        """
        pass

    def stopped(self):
        """
        Behavior after all streams have stopped
        """
        pass

    @staticmethod
    def exit():
        """
        Signal for all streams to exit
        """
        DataStream._exited.set()

    def __str__(self):
        return self.name

    def __repr__(self):
        return "%s()" % self.__class__.__name__


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

    def join(self):
        if not self.thread.daemon:
            self.thread.join()

    def _init(self):
        """
        Start the thread
        """
        self.thread.start()


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

        try:
            await self.run()
        except BaseException:
            self.stop()
            self.logger.debug("catching exception in async loop")
            self.exit()
            raise

        self.logger.debug("run finished")
        self.stop()
        self.exit()

    async def run(self):
        """
        Added async tag since this method will be asynchronous
        """
        pass
