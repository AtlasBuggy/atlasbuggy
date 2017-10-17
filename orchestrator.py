import signal
import logging
import asyncio

from log_factory import make_logger
from node import Node


class Orchestrator:
    def __init__(self, event_loop, logger=None):
        self.event_loop = event_loop
        self.name = self.__class__.__name__
        if logger is None:
            self.logger = make_logger(self.name, logging.INFO)
        else:
            self.logger = logger

        self.nodes = []
        self.loop_tasks = []
        self.exit_event = asyncio.Event(loop=event_loop)

        self.event_loop.add_signal_handler(signal.SIGINT, self.cancel_loop_tasks, self.event_loop)

    def make_logger(self, level=logging.INFO, write=False, log_format=None, file_name=None, directory=None,
                    custom_fields_fn=None):
        return make_logger(self.__class__.__name__, level, write, log_format, file_name, directory, custom_fields_fn)

    def add_nodes(self, *nodes):
        """Add the tasks associated with each node to the event loop"""
        for node in nodes:
            if node.enabled:
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
            return asyncio.sleep(0.0)
        self.exit_event.set()

        self.logger.info("halting")
        self.cancel_loop_tasks(self.event_loop)
        if len(self.nodes) > 0:
            teardown_tasks = [asyncio.ensure_future(self.teardown())]
            for node in self.nodes:
                teardown_tasks.append(asyncio.ensure_future(node.teardown()))

            return asyncio.wait(teardown_tasks)
        else:
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
                self.logger.error(task.exception())
                raise task.exception()

    # ----- subscription methods -----

    def subscribe(self, producer, consumer, service="default", message_converter=None):
        """Define a producer-consumer relationship between two nodes. """

        if not producer.enabled:
            self.logger.info("Producer '%s' isn't enabled! Ignoring consumer '%s' subscription" % (producer, consumer))
            return
        if not consumer.enabled:
            self.logger.info("Consumer '%s' isn't enabled! Ignoring subscription to producer '%s'" % (consumer, producer))
            return

        if producer not in self.nodes:
            raise RuntimeError("Producer node wasn't added!! Call add_nodes(producer_instance) in orchestrator")
        if consumer not in self.nodes:
            raise RuntimeError("Consumer node wasn't added!! Call add_nodes(consumer_instance) in orchestrator")

        if not isinstance(producer, Node):
            raise ValueError("Producer (of type '%s') is not of type Node" % str(type(producer)))
        if not isinstance(consumer, Node):
            raise ValueError("Consumer (of type '%s') is not of type Node" % str(type(consumer)))

        matched_subscription = None

        # find a suitable subscription
        for subscription in consumer.producer_subs:
            if service == subscription.requested_service:
                if subscription.expected_producer_class is None or \
                        isinstance(producer, subscription.expected_producer_class):

                    matched_subscription = subscription
                    break

        if matched_subscription is None:
            raise ValueError("No matching subscriptions found between '%s' and '%s'" % (producer, consumer))

        if message_converter is not None and not callable(message_converter):
            raise ValueError("Supplied message converter isn't a function!!")

        matched_subscription.producer_node = producer
        matched_subscription.consumer_node = consumer
        matched_subscription.set_event_loop(self.event_loop)
        matched_subscription.message_converter = message_converter
        producer.append_subscription(matched_subscription)

    def __str__(self):
        return self.name

def run_orchestrator(OrchestratorClass):
    loop = asyncio.get_event_loop()
    orchestrator = OrchestratorClass(loop)

    try:
        loop.run_until_complete(orchestrator.run())
        orchestrator.logger.info("loop finished")
    except KeyboardInterrupt:
        orchestrator.logger.info("Interrupted by user")
    finally:
        orchestrator.logger.info("halting")
        loop.run_until_complete(orchestrator.halt())
