import logging
import time
import asyncio
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
            log_level = logging.WARNING

        self.name = name
        if type(self.name) != str:
            raise ValueError("Name isn't a string: %s" % self.name)

        self.enabled = enabled

        self.asyncio_loop = None  # asyncio event loop. Assigned by Robot

        self._timestamp = None  # current time since epoch
        self.start_time = None  # stream start time. Can be set externally
        self.use_current_time = True

        self._has_started = Event()  # start flag
        self._has_stopped = Event()  # stop flag

        self.exit_when_finished = True

        # streams this stream is subscribed to referenced by subscription tag name (a dictionary of producers)
        # {subscription_tag: subscription}
        self.subscriptions = {}

        # streams subscribed to this stream referenced by service tag (a dictionary of consumers)
        # {service_tag: [subscription_1, subscription_2, subscription_3]}
        self.subscribers = {}

        # dictionary of subscription properties referenced by subscription tag name
        # contains tuples: (subscription_class, stream_class, service_tag, required_attributes, is_suggestion)
        self.required_subscriptions = {}

        # services offered by this data stream. Every stream has the default service
        # adding services will allow you to post different kinds of content
        self.subscription_services = {
            # function pointer. By default no modifications are made to the post.
            # None implies any type of message will be broadcast by the producer
            "default": (self.default_post_service, None)
        }
        self.service_suppressed_warnings = {"default"}

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

    @property
    def timestamp(self):
        if self.use_current_time:
            self._timestamp = time.time()
        return self._timestamp

    def set_current_time(self, current_time):
        self._timestamp = current_time

    def dt(self):
        """
        Time since start was called. Supply your own timestamp or use the current system time
        Overwrite time_started to change the initial time
        :return: Current time in seconds
        """
        # use the system time as current time by default. If you have another time source (e.g. log files),
        # use this method to update the stream's time

        if self.start_time is None or self.timestamp is None:
            return 0.0
        else:
            return self.timestamp - self.start_time

    def subscribe(self, subscription):
        if not isinstance(subscription, Subscription):
            raise ValueError("subscriptions must be of type Subscription: %s" % subscription)

        producer = subscription.producer_stream
        subscription.enabled = producer.enabled

        # put subscription in the table
        self.subscriptions[subscription.tag] = subscription

        # subscription now has a reference to the producer stream and consumer stream
        subscription.set_consumer(self)

        # mostly for async streams. Tell subscription whether to use the async or sync queue
        self._subscribed(subscription)

        # Add this data stream (the consumer) to the producer stream's subscriptions
        # Request a particular service
        if subscription.service in subscription.producer_stream.subscribers:
            producer.subscribers[subscription.service].append(subscription)
        else:
            producer.subscribers[subscription.service] = [subscription]

        if subscription.service != "default":
            message = "requesting '%s' service" % subscription.service
        else:
            message = ""
        self.logger.debug("'%s' %s '%s' %s" % (self, subscription.description, subscription.producer_stream, message))

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
                             required_attributes=None, required_methods=None, required_message_classes=None,
                             is_suggestion=False):
        """
        Require that this stream be subscribed to another stream
        :param tag: What the subscription tag should be
        :param subscription_class: What type of subscription it should be (None for any)
        :param stream_class: What class the producer stream should be (None for any)
        :param service_tag: The service the producer stream should provide (None for "default")
        :param required_attributes: What variables the stream should have.
            Can be a tuple of strings or one string
        :param required_methods: What methods the stream should have.
            Can be a tuple of method pointers or a single method pointer
        :param required_message_classes: What type of message the consumer should expect.
            Can be tuple of classes or a single class type. Alternatively, you can put a string containing the name
            of the class.
        :param is_suggestion: If True, this requirement will only be enforced if the stream actually subscribes.
            So there can be either no subscription or a subscription must abide by these requirements
        """
        if required_attributes is not None:
            try:
                iter(required_attributes)
            except TypeError:
                required_attributes = (required_attributes,)

        if required_methods is not None:
            try:
                iter(required_methods)
            except TypeError:
                required_methods = (required_methods,)

        if required_message_classes is not None:
            try:
                iter(required_message_classes)
            except TypeError:
                required_message_classes = (required_message_classes,)

        self.required_subscriptions[tag] = dict(
            subscription_class=subscription_class,
            stream_class=stream_class,
            service_tag=service_tag,
            required_attributes=required_attributes,
            required_methods=required_methods,
            is_suggestion=is_suggestion,
            required_message_classes=required_message_classes
        )

    def adjust_requirement(self, tag, **properties):
        """
        Adjust a required subscription

        :param tag: The tag of the requirement to adjust
        :param properties: can be subscription_class, stream_class, service_tag, required_attributes, or is_suggestion
        """
        subscription = self.required_subscriptions[tag]
        subscription.update(properties)

    def remove_requirement(self, tag):
        """Remove a subscription requirement"""
        del self.required_subscriptions[tag]

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

    def _check_subscription_tag(self, tag, is_suggestion):
        if tag not in self.subscriptions:
            # if subscription is a suggestion, don't check requirements if the subscription wasn't applied
            if is_suggestion:
                return None
            else:
                raise ValueError("Subscription tag '%s' not found in subscriptions for '%s'! "
                                 "Supplied subscriptions: %s" % (tag, self.name, self.subscriptions))
        return True

    def _check_subscription_type(self, tag, subscription_class, message):
        if subscription_class is not None and \
                        tag in self.subscriptions and \
                        type(self.subscriptions[tag]) != subscription_class:
            # check if subscription classes match
            message += "Subcription classes don't match! "
            return False, message
        else:
            return True, message

    def _check_expected_producer_class(self, producer_stream, stream_class, message):
        if stream_class is not None and type(producer_stream) != stream_class:
            # check if subscription is the correct type
            message += "Stream classes don't match! "
            return False, message
        else:
            return True, message

    def _check_service_tags(self, tag, producer_stream, service_tag, message):
        if service_tag is not None and service_tag not in producer_stream.subscription_services:
            # check if the requested service is offered by the producer stream
            message += "Service '%s' is not offered by producer stream '%s'! " % (
                service_tag, producer_stream.name)
            return False, message

        if service_tag is not None and service_tag != self.subscriptions[tag].service:
            message += "Subscribed to the wrong service! Found '%s', should be '%s'" % (
                self.subscriptions[tag].service, service_tag)
            return False, message

        return True, message

    def _check_producer_attributes(self, producer_stream, required_attributes, message):
        if required_attributes is not None:
            # check if the producer stream has the required attributes
            missing_attributes = []
            for attribute_name in required_attributes:
                if not hasattr(producer_stream, attribute_name):
                    missing_attributes.append(attribute_name)

            if len(missing_attributes) > 0:
                message += "%s doesn't have the required attributes: %s" % (
                    producer_stream.name, missing_attributes)
                return False, message
        return True, message

    def _check_producer_methods(self, producer_stream, required_methods, message):
        if required_methods is not None:
            missing_methods = []
            for method_name in required_methods:
                if not hasattr(producer_stream, method_name) or \
                        not callable(getattr(producer_stream, method_name)):
                    missing_methods.append(method_name)

            if len(missing_methods) > 0:
                message += "%s doesn't have the required methods: %s" % (
                    producer_stream.name, missing_methods)
                return False, message
        return True, message

    def _check_subscription_messages(self, producer_stream, required_message_classes, message):
        satisfied = True
        if required_message_classes is not None:
            for service_tag, (service_fn, message_class) in producer_stream.subscription_services.items():
                if message_class is None:
                    continue

                for required_message_class in required_message_classes:
                    if type(required_message_class) == str:
                        if message_class.__name__ != required_message_class:
                            satisfied = False
                    else:
                        if message_class != required_message_class:
                            satisfied = False

                    if not satisfied:
                        if type(required_message_class) == type:
                            required_message_class_str = required_message_class.__name__
                        else:
                            required_message_class_str = required_message_class

                        message += \
                            "Consumer '%s' expects a message of type named '%s' from producer '%s' " \
                            "for the service '%s'. %s broadcasts the message type '%s' for the service '%s'" % (
                                self.name, required_message_class_str, producer_stream.name, service_tag,
                                producer_stream.name, message_class.__name__, service_tag
                            )
                        break
                if not satisfied:
                    break
        return satisfied, message

    def _check_subscriptions(self):
        """Check if all required subscriptions have been satisfied"""
        self.logger.debug("Checking subscriptions")

        for tag, subscr_props in self.required_subscriptions.items():
            message = ""

            subscription_class = subscr_props["subscription_class"]
            stream_class = subscr_props["stream_class"]
            service_tag = subscr_props["service_tag"]
            required_methods = subscr_props["required_methods"]
            required_attributes = subscr_props["required_attributes"]
            is_suggestion = subscr_props["is_suggestion"]
            required_message_classes = subscr_props["required_message_classes"]

            result = self._check_subscription_tag(tag, is_suggestion)
            if result is None:
                continue

            subscription_types_match, message = \
                self._check_subscription_type(tag, subscription_class, message)
            producer_stream = self.subscriptions[tag].producer_stream

            producer_class_matches, message = \
                self._check_expected_producer_class(producer_stream, stream_class, message)
            service_tags_match, message = \
                self._check_service_tags(tag, producer_stream, service_tag, message)

            producer_attibutes_match, message = \
                self._check_producer_attributes(producer_stream, required_attributes, message)

            producer_methods_match, message = \
                self._check_producer_methods(producer_stream, required_attributes, message)

            messages_match, message = \
                self._check_subscription_messages(producer_stream, required_message_classes, message)

            # throw an error if any of the above requirements failed
            satisfied = (
                subscription_types_match and
                producer_class_matches and
                producer_attibutes_match and
                producer_methods_match and
                messages_match
            )

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
                for subscr_props in subscriptions:
                    non_existent_services.append((subscr_props.consumer_stream.name, requested_service))
        if len(non_existent_services) > 0:
            message = ""
            for name, service in non_existent_services:
                message += "\t%s is requesting '%s'\n" % (name, service)
            raise ValueError("The following services were requested from '%s' that don't exist:\n%s" % (
                self.name, message))

        # Check if all services offered by this stream are being used
        if len(self.subscribers) > 0:  # only check if services are being used if there are any subscribers
            unused_services = self.subscription_services.keys() - self.subscribers.keys()
            unused_services = unused_services - self.service_suppressed_warnings
            if len(unused_services) > 0:
                message = str(list(unused_services))[1:-1]
                self.logger.warning("The following subscription services are not being consumed: %s" % message)

    def post(self, data, service="default", **kwargs):
        """
        Post data to subscribed consumer streams

        :param data: Data to post
        :param service: which service to post data to
        """
        pass

    @asyncio.coroutine
    def async_post(self, data, service="default", **kwargs):
        """
        Post data to subscribed consumer streams using the async method

        :param data: Data to post 
        :param service: which service to post data to
        """
        if service in self.subscribers:
            for subscription in self.subscribers[service]:
                if subscription.enabled:
                    assert service == subscription.service
                    post_fn, message_class = self.subscription_services[service]

                    if message_class != type(data):
                        raise ValueError("posted data of type '%s' does not match type '%s'" % (
                            type(data), message_class))

                    yield from subscription.async_post(post_fn(data), **kwargs)
        yield from asyncio.sleep(0.0)

    def sync_post(self, data, service="default", **kwargs):
        """
        Post data to subscribed consumer streams using the sync method

        :param data: Data to post 
        :param service: which service to post data to
        """
        if service in self.subscribers:
            for subscription in self.subscribers[service]:
                if subscription.enabled:
                    assert service == subscription.service
                    post_fn, message_class = self.subscription_services[service]

                    if message_class != type(data):
                        raise ValueError("posted data of type '%s' does not match type '%s'" % (
                            type(data), message_class))

                    subscription.sync_post(post_fn(data), **kwargs)

    def default_post_service(self, data):
        """
        By default, data posted isn't modified. If you're posting arrays, create a method
        that calls .copy() on the data before posting.

        :param data: data to post
        :return: modified (copied) data to post
        """
        return data

    def add_service(self, service_tag, post_fn=None, message_class=None, suppress_unused_warning=False):
        """
        Call this method in the stream's constructor to add a new service.
        :param service_tag: The name of this service
        :param post_fn: Default function used is self.default_post_service
            You should supply an alternate post function if you're posting lists or dictionaries (references to objects)
            For those situations call .copy() on the data before returning it
            Don't call self.post inside that method
        :param message_class: The class type of messages being 
        :param suppress_unused_warning: If this service isn't used by any consumers, don't print a warning
        """
        if post_fn is None:
            post_fn = self.default_post_service
        assert callable(post_fn), "post_fn isn't a function pointer!! '%s'" % post_fn
        assert type(message_class) == type, "message_class isn't a type!! '%s'" % message_class

        self.subscription_services[service_tag] = (post_fn, message_class)
        if suppress_unused_warning:
            self.service_suppressed_warnings.add(service_tag)

    def adjust_service(self, service_tag, post_fn=None, message_class=None, suppress_unused_warning=False):
        old_post_fn, old_message_class = self.subscription_services[service_tag]
        if post_fn is not None:
            assert callable(post_fn), "post_fn isn't a function pointer!! '%s'" % post_fn
        else:
            post_fn = old_post_fn

        if message_class is not None:
            assert type(message_class) == type, "message_class isn't a type!! '%s'" % message_class
        else:
            message_class = old_message_class

        self.subscription_services[service_tag] = (post_fn, message_class)

        if not suppress_unused_warning:
            self.service_suppressed_warnings.remove(service_tag)
        else:
            self.service_suppressed_warnings.add(service_tag)

    def remove_service(self, service_tag):
        del self.subscription_services[service_tag]
        self.service_suppressed_warnings.remove(service_tag)

    def _receive_log(self, log_level, message, line_info):
        self.set_current_time(line_info["timestamp"])
        self.receive_log(log_level, message, line_info)

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
        """Callback for stream_start. Time has started, run has not been called."""
        pass

    def started(self):
        """Callback for _start. _run has been called."""
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
        """Internal extra startup behavior"""
        pass

    def apply_subs(self):
        self._check_subscriptions()
        self.logger.debug("applying subscriptions: %s" % str(self.subscriptions))
        self.take(self.subscriptions)

    def _start(self):
        """Wrapper for starting the stream"""
        if not self._has_started.is_set():  # only call _start once
            if not self.enabled:
                self.logger.debug("stream not enabled")
                return

            self.logger.debug("starting")
            self._has_started.set()
            self.start_time = self.time_started()

            self.start()
            self._init()

    def has_started(self):
        return self._has_started.is_set()

    def _run(self):
        """Wrapper for running stream"""

        try:
            self.started()
            self.logger.debug("calling run")
            self.run()
            self.logger.debug("%s exiting run" % self.name)
        except BaseException as error:
            self.logger.debug("catching exception in run")
            self.logger.exception(error)
            raise
        finally:
            self.logger.debug("run finished")
            if self.exit_when_finished:
                self.exit()
            self._stop()  # in threads, stop is called inside the thread instead to avoid race conditions

    def run(self):
        """Main behavior of the stream. Put 'while self.running():' in this method"""
        pass

    def update(self):
        """Optional method to be called inside run's while loop"""
        pass

    def _stop(self):
        """Wrapper for stopping the stream. Assumes that exit has been set"""
        if not self.enabled:
            return
        if not self._has_stopped.is_set():  # only call _stop once
            self._has_stopped.set()
            self.logger.debug("stopping")
            self.stop()
            self.logger.debug("stopped")

    def stop(self):
        """Stop behavior of the stream"""
        pass

    def has_stopped(self):
        return self._has_stopped.is_set()

    def stopped(self):
        """Behavior after all streams have stopped"""
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
