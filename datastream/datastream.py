import logging
import time
from threading import Event


class DataStream:
    _exited = Event()  # signal to exit
    _log_info = {}

    def __init__(self, enabled, name=None, log_level=None, version="1.0"):
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
        self.version = version

        self.enabled = enabled

        self.asyncio_loop = None

        self.timestamp = None  # current time since epoch
        self.start_time = None  # stream start time. Can be set externally

        self._has_started = Event()  # self._start flag
        self._has_stopped = Event()  # self._stop flag

        self.subscriptions = {}
        self.subscribers = []
        self._required_subscriptions = {}

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

        stream_filter = logging.Filter()
        stream_filter.filter = self.log_filter

        self.logger.addFilter(stream_filter)

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

    def subscribe(self, subscription):
        self.subscriptions[subscription.tag] = subscription
        subscription.stream.subscribers.append(subscription)
        self.logger.debug("'%s' %s '%s'" % (self, subscription.description, subscription.stream))

    def take(self, subscriptions):
        pass

    def require_subscription(self, tag, subscription_class=None, stream_class=None):
        self._required_subscriptions[tag] = (subscription_class, stream_class)

    def _check_subscriptions(self):
        self.logger.debug("Checking subscriptions")
        for tag, (subscription_class, stream_class) in self._required_subscriptions.items():
            satisfied = 0
            if tag not in self.subscriptions:
                satisfied = 1

            if subscription_class is not None and type(self.subscriptions[tag]) != subscription_class:
                satisfied = 2

            if stream_class is not None and type(self.subscriptions[tag].stream) != stream_class:
                satisfied = 3

            if satisfied != 0:
                message = ""
                if subscription_class is not None or stream_class is not None:
                    message += "This streams requires "
                    if subscription_class is not None:
                        message += "a subscription of type '%s'" % subscription_class.__name__

                    if stream_class is not None:
                        if subscription_class is not None:
                            message += " and "
                        message += "a stream of type '%s'. " % stream_class.__name__
                    else:
                        message += ". "

                if satisfied == 1:
                    message += "Tags don't match!"
                elif satisfied == 2:
                    message += "Subcription classes don't match!"
                elif satisfied == 3:
                    message += "Stream classes don't match!"

                raise ValueError("Required subscription '%s' not found! " + message)

    def post(self, data):
        for subscription in self.subscribers:
            if subscription.enabled:
                subscription.post(self.post_behavior(data))

                if subscription.callback is not None:
                    subscription.callback(subscription.tag)

    def post_behavior(self, data):
        return data

    def receive_post(self, tag):
        pass

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

    def log_filter(self, record):
        record.version = self.version
        return True

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

            self.take(self.subscriptions)
            self._check_subscriptions()
            self.logger.debug("starting")
            self._has_started.set()
            self.start_time = self.time_started()
            self.start()
            self._init()

    def has_started(self):
        return self._has_started.is_set()

    def _run(self):
        """
        Wrapper for running stream
        """

        try:
            self.logger.debug("calling run")
            self.run()
        except BaseException:
            self.logger.debug("catching exception in threaded loop")
            self._stop()  # in threads, stop is called inside the thread instead to avoid race conditions
            self.exit()
            raise

        self.logger.debug("run finished")
        self._stop()
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

    def has_stopped(self):
        return self._has_stopped.is_set()

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

    def version(self):
        return self.parse_version(self.version)

    @staticmethod
    def parse_version(version_string):
        return tuple(map(int, (version_string.split("."))))

    def __str__(self):
        return self.name

    def __repr__(self):
        return "%s()" % self.__class__.__name__
