import logging
import time
from threading import Event
from ..subscriptions import Subscription


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

        self.asyncio_loop = None

        self.timestamp = None  # current time since epoch
        self.start_time = None  # stream start time. Can be set externally

        self._has_started = Event()  # self._start flag
        self._has_stopped = Event()  # self._stop flag

        self.subscriptions = {}
        self.subscribers = {}
        self._required_subscriptions = {}
        self.subscription_services = {
            "default": self.default_post_service
        }

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
        if not isinstance(subscription, Subscription):
            raise ValueError("subscriptions must be of type Subscription: %s" % subscription)
        self.subscriptions[subscription.tag] = subscription
        subscription.set_consumer(self)
        
        self._subscribed(subscription)

        # consumer is adding a request for a service from the producer
        producer = subscription.producer_stream
        if subscription.service in subscription.producer_stream.subscribers:
            producer.subscribers[subscription.service].append(subscription)
        else:
            producer.subscribers[subscription.service] = [subscription]

        self.logger.debug("'%s' %s '%s'" % (self, subscription.description, subscription.producer_stream))

    def _subscribed(self, subscription):
        """
        Internal post subscription behavior
        :param subscription: Instance of Subscription class
        """
        pass

    def take(self, subscriptions):
        pass

    def require_subscription(self, tag, subscription_class=None, stream_class=None, service=None,
                             required_attributes=None, is_suggestion=False):
        if required_attributes is not None:
            assert type(required_attributes) == tuple
        self._required_subscriptions[tag] = (
            subscription_class, stream_class, service, required_attributes, is_suggestion)

    def is_subscribed(self, tag):
        return tag in self.subscriptions and \
               self.subscriptions[tag].enabled and \
               self.subscriptions[tag].producer_stream is not None and \
               self.subscriptions[tag].producer_stream.enabled

    def check_subscriptions(self):
        self.logger.debug("Checking subscriptions")

        # check if all required subscriptions have been satisfied
        for tag, (subscription_class, stream_class, service, required_attributes,
                  is_suggestion) in self._required_subscriptions.items():
            satisfied = True
            message = ""
            if tag not in self.subscriptions:
                # if subscription is a suggestion, don't check requirements if the subscription wasn't applied
                if is_suggestion:
                    continue
                message += "Tag not found! "
                satisfied = False

            if subscription_class is not None and \
                            tag in self.subscriptions and \
                            type(self.subscriptions[tag]) != subscription_class:
                message += "Subcription classes don't match! "
                satisfied = False

            producer_stream = self.subscriptions[tag].producer_stream

            if stream_class is not None and type(producer_stream) != stream_class:
                message += "Stream classes don't match! "
                satisfied = False

            if service is not None and service not in producer_stream.subscription_services:
                message += "Service '%s' not offered by producer stream '%s'! " % (
                    service, producer_stream.name)
                satisfied = False

            if required_attributes is not None:
                missing_attributes = []
                for attribute_name in required_attributes:
                    if not hasattr(producer_stream, attribute_name):
                        missing_attributes.append(attribute_name)

                if len(missing_attributes) > 0:
                    message += "%s doesn't have the required attributes: %s" % (
                        producer_stream.name, missing_attributes)
                    satisfied = False

            if not satisfied:
                if subscription_class is not None or stream_class is not None:
                    if subscription_class is None:
                        subscription_class_requirement = "any"
                    else:
                        subscription_class_requirement = subscription_class.__name__

                    if stream_class is None:
                        stream_class_requirement = "any"
                    else:
                        stream_class_requirement = stream_class.__name__

                    message += "\n%s requires the following subscription:\n" \
                               "\tsubscription type: '%s'\n\ttag: '%s'\n\tproducer class: '%s'\n\tservice tag: '%s'" % (
                                   self.name, subscription_class_requirement, tag, stream_class_requirement, service
                               )

                raise ValueError("Required subscription not found! " + message)

        non_existent_services = []
        for requested_service, subscriptions in self.subscribers.items():
            if requested_service not in self.subscription_services.keys():
                for subscription in subscriptions:
                    non_existent_services.append((subscription.consumer_stream.name, requested_service))
        if len(non_existent_services) > 0:
            raise ValueError("The following services were requested from '%s' that don't exist:\n\t%s" % (
                self.name, str(["%s: %s" % (name, service) for name, service in non_existent_services])[1:-1]))

        if len(self.subscribers) > 0:
            unused_services = list(self.subscription_services.keys() - self.subscribers.keys())
            if len(unused_services) > 0:
                self.logger.warning("The following subscription services are not being consumed: %s" % unused_services)

    def post(self, data, service="default"):
        pass

    def default_post_service(self, data):
        return data

    def add_service(self, service_tag, post_fn=None):
        if post_fn is None:
            post_fn = self.default_post_service
        assert callable(post_fn)
        self.subscription_services[service_tag] = post_fn

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
        return True

    def start(self):
        """
        Callback for stream_start. Time has started, run has not been called.
        :return:
        """
        pass

    def started(self):
        pass

    @staticmethod
    def is_running():
        """
        Check if stream is running. Use this in your while loops in your run methods:

        while self.is_running():
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

            self.check_subscriptions()
            self.logger.debug("applying subscriptions: %s" % str(self.subscriptions))
            self.take(self.subscriptions)

            self.start()
            self._init()

    def has_started(self):
        return self._has_started.is_set()

    def _run(self):
        """
        Wrapper for running stream
        """

        try:
            self.started()
            self.logger.debug("calling run")
            self.run()
            self.logger.debug("%s exiting run" % self.name)
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

    @staticmethod
    def parse_version(version_string):
        return tuple(map(int, (version_string.split("."))))

    def __str__(self):
        return self.name

    def __repr__(self):
        return "%s()" % self.__class__.__name__
