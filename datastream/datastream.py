import logging
import time
from threading import Event
from ..subscriptions import Subscription


class DataStream:
    _exited = Event()  # signal to exit
    _log_info = {}  # information about the logger

    def __init__(self, enabled=True, log_level=None, name=None):
        """
        Initialization. No streams have started yet.
        :param enabled: Include this stream in the runtime
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

        self.asyncio_loop = None  # asyncio event loop. Assigned by Robot

        self.timestamp = None  # current time since epoch
        self.start_time = None  # stream start time. Can be set externally

        self._has_started = Event()  # start flag
        self._has_stopped = Event()  # stop flag

        # streams this stream is subscribed to referenced by subscription tag name (a dictionary of producers)
        # {subscription_tag: subscription}
        self.subscriptions = {}

        # streams subscribed to this stream referenced by service tag (a dictionary of consumers)
        # {service_tag: [subscription_1, subscription_2, subscription_3]}
        self.subscribers = {}

        # dictionary of subscription properties referenced by subscription tag name
        # contains tuples: (subscription_class, stream_class, service_tag, required_attributes, is_suggestion)
        self._required_subscriptions = {}

        # services offered by this data stream. Every stream has the default service
        # adding services will allow you to post different kinds of content
        self.subscription_services = {
            "default": self.default_post_service  # function pointer. By default no modifications are made to the post
        }

        # instance of logging. Use this instance to print debug statement and log
        self.logger = logging.getLogger(self.name)

        # make sure robot has instantiated the log info before this stream
        if len(DataStream._log_info) == 0:
            raise ValueError("Declare Robot before initializing any streams.")

        # robot's log level takes priority over individual streams
        if DataStream._log_info["log_level"] < log_level:
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
        Time since start was called. Supply your own timestamp or use the current system time
        Overwrite time_started to change the initial time
        :return: Current time in seconds
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

        # put subscription in the table
        self.subscriptions[subscription.tag] = subscription

        # subscription now has a reference to the producer stream and consumer stream
        subscription.set_consumer(self)

        # mostly for async streams. Tell subscription whether to use the async or sync queue
        self._subscribed(subscription)

        # Add this data stream (the consumer) to the producer stream's subscriptions
        # Request a particular service
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
        """
        Take subscriptions and assign them to object variables.

        Example:
            self.some_producer = subscriptions[self.some_producer_tag].get_stream()

            # you requested an Update or Feed subscription:
            self.some_producer_feed = subscriptions[self.some_producer_tag].get_feed()
        :param subscriptions: dictionary of subscriptions referenced by subscription tag
        """
        pass

    def require_subscription(self, tag, subscription_class=None, stream_class=None, service_tag=None,
                             required_attributes=None, is_suggestion=False):
        """
        Require that this stream be subscribed to another stream
        :param tag: What the subscription tag should be
        :param subscription_class: What type of subscription it should be (None for any)
        :param stream_class: What class the producer stream should be (None for any)
        :param service_tag: The service the producer stream should provide (None for "default")
        :param required_attributes: What variables or methods the stream should have
        :param is_suggestion: If True, this requirement will only be enforced if the stream actually subscribes.
            So there can be either no subscription or a subscription must abide by these requirements
        """
        if required_attributes is not None:
            assert type(required_attributes) == tuple
        self._required_subscriptions[tag] = (
            subscription_class, stream_class, service_tag, required_attributes, is_suggestion)

    def is_subscribed(self, tag):
        """
        Check if this stream is subscribed to subscription that matches the tag.

        :param tag: subscription tag name
        :return: True if this stream is subscribed. This is true if a subscription has been added with that tag,
            if the subscription is enabled, and if the producer stream is enabled
        """
        return (tag in self.subscriptions and
                self.subscriptions[tag].enabled and
                self.subscriptions[tag].producer_stream is not None and
                self.subscriptions[tag].producer_stream.enabled)

    def check_subscriptions(self):
        """
        Check if all required subscriptions have been satisfied
        """
        self.logger.debug("Checking subscriptions")

        for tag, (subscription_class, stream_class, service_tag, required_attributes,
                  is_suggestion) in self._required_subscriptions.items():
            satisfied = True
            message = ""
            if tag not in self.subscriptions:
                # if subscription is a suggestion, don't check requirements if the subscription wasn't applied
                if is_suggestion:
                    continue
                else:
                    raise ValueError("Subscription tag '%s' not found in subscriptions for '%s'!" % (tag, self.name))

            if subscription_class is not None and \
                            tag in self.subscriptions and \
                            type(self.subscriptions[tag]) != subscription_class:
                # check if subscription classes match
                message += "Subcription classes don't match! "
                satisfied = False

            producer_stream = self.subscriptions[tag].producer_stream

            if stream_class is not None and type(producer_stream) != stream_class:
                # check if subscription is the correct type
                message += "Stream classes don't match! "
                satisfied = False

            if service_tag is not None and service_tag not in producer_stream.subscription_services:
                # check if the requested service is offered by the producer stream
                message += "Service '%s' is not offered by producer stream '%s'! " % (
                    service_tag, producer_stream.name)
                satisfied = False

            if required_attributes is not None:
                # check if the producer stream has the required attributes
                missing_attributes = []
                for attribute_name in required_attributes:
                    if not hasattr(producer_stream, attribute_name):
                        missing_attributes.append(attribute_name)

                if len(missing_attributes) > 0:
                    message += "%s doesn't have the required attributes: %s" % (
                        producer_stream.name, missing_attributes)
                    satisfied = False

            # throw an error if any of the above requirements failed
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
                                   self.name, subscription_class_requirement, tag, stream_class_requirement, service_tag
                               )

                raise ValueError("Required subscription not found! " + message)

        # check if any of the streams subscribed to this stream are asking for services that don't exist
        non_existent_services = []
        for requested_service, subscriptions in self.subscribers.items():
            if requested_service not in self.subscription_services.keys():
                for subscription in subscriptions:
                    non_existent_services.append((subscription.consumer_stream.name, requested_service))
        if len(non_existent_services) > 0:
            raise ValueError("The following services were requested from '%s' that don't exist:\n\t%s" % (
                self.name, str(["%s: %s" % (name, service) for name, service in non_existent_services])[1:-1]))

        # Check if all services offered by this stream are being used
        if len(self.subscribers) > 0:
            unused_services = list(self.subscription_services.keys() - self.subscribers.keys())
            if len(unused_services) > 0:
                self.logger.warning("The following subscription services are not being consumed: %s" % unused_services)

    def post(self, data, service="default"):
        """
        Post data to subscribed consumer streams

        :param data: Data to post
        :param service: which service to post data to
        """
        pass

    def default_post_service(self, data):
        """
        By default, data posted isn't modified. If you're posting arrays, create a method
        that calls .copy() on the data before posting.

        :param data: data to post
        :return: modified (copied) data to post
        """
        return data

    def add_service(self, service_tag, post_fn=None):
        """
        Call this method in the stream's constructor to add a new service.
        :param service_tag: The name of this service
        :param post_fn: Default function used is self.default_post_service
            You should supply an alternate post function if you're posting lists or dictionaries (references to objects)
            For those situations call .copy() on the data before returning it
            Don't call self.post inside that method
        """
        if post_fn is None:
            post_fn = self.default_post_service
        assert callable(post_fn)
        self.subscription_services[service_tag] = post_fn

    def receive_log(self, log_level, message, line_info):
        """
        If LogParser is given to Robot and LogParser subscribes to this stream, it will give any matching log
        messages it finds in a log file. This includes error and debug messages

        :param log_level: type of log message
        :param message: string found in the log file
        :param line_info: a dictionary of information discovered. Keys in the dictionary:
            timestamp, year, month, day, hour, minute, second, millisecond,
            name - name of the stream that produced the message,
            message, linenumber, filename, loglevel
        """
        pass

    def log_filter(self, record):
        """
        Deprecated functionality. Formatting behavior for log messages
        See: https://stackoverflow.com/questions/17558552/how-do-i-add-custom-field-to-python-log-format-string

        Example:
        record.version = self.version_num

        version is now a field used by the logger for string formatting.
        """
        return True

    def start(self):
        """
        Callback for stream_start. Time has started, run has not been called.
        """
        pass

    def started(self):
        """
        Callback for _start. _run has been called.
        """
        pass

    @staticmethod
    def is_running():
        """
        Check if stream is running. Use this in your while loops in your run methods:

        while self.is_running():
            ...
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
        pass

    def _start(self):
        """
        Wrapper for starting the stream
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
        except BaseException as error:
            self.logger.debug("catching exception in run")
            self.logger.exception(error)
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
