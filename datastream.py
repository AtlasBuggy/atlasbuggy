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

        self.timestamp = None  # current time since epoch
        self.start_time = None  # stream start time. Can be set externally

        self.started = Event()  # self._start flag
        self.stopped = Event()  # self._stop flag
        self.exited = Event()  # signal to exit
        DataStream._exit_events.append(self.exited)  # give streams ability to close each other

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
    def all_running():
        """
        Check if all exit events are False
        :return: False when all streams have called self.exit
          All streams have exited when:
            - their run methods have completed
            - when Robot catches an exception
            - DataStream.exit_all() is called
            - All streams have called self.exit themselves
        """
        return not all([result.is_set() for result in DataStream._exit_events])

    @staticmethod
    def any_stopped():
        """
        Check if any exit events are True
        :return: False when any stream has called self.exit
        """
        return any([result.is_set() for result in DataStream._exit_events])

    def running(self):
        """
        Check if stream is running. Use this in your while loops in your run methods:
        
        while self.running():
            ...
        :return:
        """
        return not self.exited.is_set()

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
        if not self.started.is_set():  # only call _start once
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
        Wrapper for running stream
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

    def _stop(self):
        """
        Wrapper for stopping the stream. Assumes that exit has been set
        """
        if not self.enabled:
            return
        if not self.stopped.is_set():  # only call _stop once
            self.stopped.set()
            self.logger.debug("stopping")
            self.stop()
            self.logger.debug("closed")

    def stop(self):
        """
        Stop behavior of the stream
        """
        pass

    def exit(self):
        """
        Signal for this stream to exit
        """
        self.logger.debug("exiting")
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
        try:
            self.run()
        except BaseException:
            self.threaded_stop()
            self.logger.debug("catching exception in threaded loop")
            self.exit()
            raise

        self.logger.debug("run finished")
        self.threaded_stop()
        self.exit()

    def threaded_stop(self):
        """
        Specialized method. If you want a close method that is called within the method,
        use this method instead of self.stop
        :return: 
        """
        pass

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
        self.logger.debug("run finished, exiting")
        self.exit()

    async def run(self):
        """
        Added async tag since this method will be asynchronous
        """
        pass

    def __repr__(self):
        return "<%s, enabled=%s, asynchronous>" % (self.__class__.__name__, self.enabled)
