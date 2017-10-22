import sys
import time
import signal
import asyncio
import traceback

from .log.factory import make_logger
from .log import default


class Orchestrator:
    def __init__(self, event_loop, logger=None):
        self.event_loop = event_loop
        self.name = self.__class__.__name__
        if not self.is_logger_created():
            if logger is None:
                self.logger, self.file_name, self.directory = make_logger(self.name, default.default_settings)
            else:
                self.logger = logger
                self.file_name = self.directory = ""

        self.nodes = []
        self.loop_tasks = []
        self.teardown_tasks = []
        self.exit_event = asyncio.Event(loop=event_loop)

        self.event_loop.add_signal_handler(signal.SIGINT, self.cancel_loop_tasks, self.event_loop)

        self.start_time = time.time()

    @staticmethod
    def set_default(**kwargs):
        default.default_settings.update(kwargs)

    def set_logger(self, *args, **kwargs):
        if self.is_logger_created():
            raise ValueError("A logger was created for this node already. Call this before the call to super().")
        self.logger, self.file_name, self.directory = make_logger(self.name, default.default_settings, *args, **kwargs)

    def is_logger_created(self):
        return hasattr(self, "logger")

    def add_nodes(self, *nodes):
        """Add the tasks associated with each node to the event loop"""
        for node in nodes:
            if node.enabled:
                node.event_loop = self.event_loop
                self.nodes.append(node)

    # ----- event order methods -----

    @asyncio.coroutine
    def setup(self):
        """Default start up behavior for Orchestrator"""
        self.logger.info("setup")

    @asyncio.coroutine
    def loop(self):
        """Default run behavior for Orchestrator"""
        yield from self.exit_event.wait()

    @asyncio.coroutine
    def teardown(self):
        """Default stopping behavior for Orchestrator"""
        self.logger.info("teardown")

    def halt(self):
        """Shutdown all node and Orchestrator tasks"""
        if self.exit_event.is_set():
            self.logger.info("already halted")
            return

        self.exit_event.set()

        self.cancel_loop_tasks(self.event_loop)
        self.logger.info("halting")

        end_time = time.time()
        self.logger.info("Session took %ss to complete" % (end_time - self.start_time))

        if len(self.nodes) > 0:
            self.teardown_tasks = [asyncio.ensure_future(self.teardown())]
            for node in self.nodes:
                self.teardown_tasks.append(asyncio.ensure_future(node.teardown()))
                node._internal_teardown()

            return asyncio.wait(self.teardown_tasks)

        return asyncio.sleep(0.0)

    def run(self):
        """First call each node's startup task then return the collected node coroutines to run indefinitely"""
        self.exit_event.clear()

        self.logger.debug("Adding setup tasks. Apply subscriptions")
        setup_tasks = [asyncio.ensure_future(self.setup())]
        for node in self.nodes:
            node.take()
            setup_tasks.append(asyncio.ensure_future(node.setup()))

        self.logger.debug("Running set up tasks (%s)" % (len(setup_tasks)))
        self.event_loop.run_until_complete(asyncio.wait(setup_tasks))

        self.logger.debug("Adding loop tasks")
        self.loop_tasks.append(asyncio.ensure_future(self.loop()))
        for node in self.nodes:
            self.loop_tasks.append(asyncio.ensure_future(node.loop()))

        self.logger.debug("Running loop tasks (%s)" % (len(self.loop_tasks)))
        return asyncio.wait(self.loop_tasks, return_when=asyncio.FIRST_COMPLETED)

    def cancel_loop_tasks(self, loop):
        """Cancel all running loop node and Orchestrator tasks"""

        self.logger.debug("%s tasks to cancel" % (len(self.loop_tasks)))
        for task in self.loop_tasks:
            result = task.cancel()
            self.logger.debug("Cancelling %s: %s" % (task, result))

            if task.cancelled():
                self.logger.debug("Task '%s' was cancelled" % task)
            elif task.done() and task.exception() is not None:
                try:
                    raise task.exception()
                except:
                    info = sys.exc_info()
                    stack_trace = traceback.format_exception(*info)
                    self.logger.error("".join(stack_trace))

                # exceptions.append(task.exception())

        # for exception in exceptions:
        #     traceback.print_exception(type(exception), exception, )

    # ----- subscription methods -----

    def subscribe(self, producer, consumer, tag, message_converter=None):
        """Define a producer-consumer relationship between two nodes. """

        if not producer.enabled:
            self.logger.info("Producer '%s' isn't enabled! Ignoring consumer '%s' subscription" % (producer, consumer))
            return
        if not consumer.enabled:
            self.logger.info(
                "Consumer '%s' isn't enabled! Ignoring subscription to producer '%s'" % (consumer, producer))
            return

        if producer not in self.nodes:
            raise RuntimeError("Producer node wasn't added!! Call add_nodes(producer_instance) in orchestrator")
        if consumer not in self.nodes:
            raise RuntimeError("Consumer node wasn't added!! Call add_nodes(consumer_instance) in orchestrator")

        matched_subscription = None

        # find a suitable subscription
        for subscription in consumer.producer_subs:
            if subscription.tag == tag:

                if subscription.required_attributes is not None:
                    missing_attributes = []
                    for attribute_name in subscription.required_attributes:
                        if not hasattr(producer, attribute_name):
                            missing_attributes.append(attribute_name)

                    if len(missing_attributes) > 0:
                        raise ValueError("Producer '%s' is missing attributes requested by consumer '%s': '%s'" % (
                            producer, consumer, missing_attributes
                        ))

                if subscription.required_methods is not None:
                    missing_methods = []
                    for method_name in subscription.required_methods:
                        if not hasattr(producer, method_name) or not callable(getattr(producer, method_name)):
                            missing_methods.append(method_name)

                    if len(missing_methods) > 0:
                        raise ValueError("Producer '%s' is missing methods requested by consumer '%s': '%s'" % (
                            producer, consumer, missing_methods
                        ))

                if subscription.expected_producer_classes is None:
                    matched_subscription = subscription
                    break
                else:
                    for expected_producer_class in subscription.expected_producer_classes:
                        if isinstance(producer, expected_producer_class):
                            matched_subscription = subscription
                            break
                    if matched_subscription is not None:
                        break

        if matched_subscription is None:
            raise ValueError("No matching subscriptions found between '%s' and '%s'" % (producer, consumer))

        if message_converter is not None and not callable(message_converter):
            raise ValueError("Supplied message converter isn't a function!!")

        self.logger.info("'%s' is subscribing to '%s' with the tag '%s'" % (consumer, producer, tag))
        matched_subscription.set_nodes(producer, consumer)
        matched_subscription.set_event_loop(self.event_loop)
        matched_subscription.message_converter = message_converter
        consumer.subscription_tags.add(tag)

        producer.append_subscription(matched_subscription)

    def __str__(self):
        return self.name


def run(OrchestratorClass):
    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    orchestrator = OrchestratorClass(loop)

    try:
        loop.run_until_complete(orchestrator.run())
        orchestrator.logger.info("loop finished")
    except KeyboardInterrupt:
        orchestrator.logger.info("Interrupted by user")
    finally:
        orchestrator.logger.info("closing orchestrator")

    halt_task = orchestrator.halt()
    loop.run_until_complete(halt_task)
    loop.close()
