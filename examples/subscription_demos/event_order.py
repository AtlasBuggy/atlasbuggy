import time
import asyncio
import traceback
from atlasbuggy import DataStream, AsyncStream, ThreadedStream, Robot
from atlasbuggy.subscriptions import *

enable_trackback = True


def get_traceback():
    if enable_trackback:
        stack_trace = traceback.format_stack()
        return ":\n" + "".join(stack_trace[:-1])
    else:
        return ""


class OrderDemoStatic(DataStream):
    def start(self):
        self.logger.info("start" + get_traceback())

    def started(self):
        self.logger.info("started" + get_traceback())

    def take(self, subscriptions):
        self.logger.info("take" + get_traceback())

    def run(self):
        self.logger.info("run" + get_traceback())

    def stop(self):
        self.logger.info("stop" + get_traceback())

    def stopped(self):
        self.logger.info("stopped" + get_traceback())


class OrderDemoAsync(AsyncStream):
    def start(self):
        self.logger.info("start" + get_traceback())

    def started(self):
        self.logger.info("started" + get_traceback())

    def take(self, subscriptions):
        self.logger.info("take" + get_traceback())

    async def run(self):
        self.logger.info("run" + get_traceback())
        await asyncio.sleep(0.0)

    def stop(self):
        self.logger.info("stop" + get_traceback())

    def stopped(self):
        self.logger.info("stopped" + get_traceback())


class OrderDemoThreaded(ThreadedStream):
    def start(self):
        self.logger.info("start" + get_traceback())

    def started(self):
        self.logger.info("started" + get_traceback())

    def take(self, subscriptions):
        self.logger.info("take" + get_traceback())

    def run(self):
        self.logger.info("run" + get_traceback())

    def stop(self):
        self.logger.info("stop" + get_traceback())

    def stopped(self):
        self.logger.info("stopped" + get_traceback())


class ImportantMethods(AsyncStream):
    # methods to not override:
    #   dt, subscribe, require_subscription, adjust_subscription, post, add_service, is_running, apply_subs,
    #   has_started, has_stopped, exit

    def __init__(self):
        super(ImportantMethods, self).__init__()

        # ----- init methods -----
        # !!! Make sure to call these after calling super().__init__ and not before !!!

        self.some_tag = "some stream"
        self.some_stream = None
        self.require_subscription(self.some_tag)

        self.adjust_requirement(
            self.some_tag,
            # change properties of some_subscription.
            # this is for changing or overriding the subscriptions of super classes
        )

        self.some_other_tag = "some other stream"
        self.require_subscription(self.some_other_tag)
        self.remove_requirement(self.some_other_tag)  # remove the subscription from a super class

        self.some_service = "new_service"
        self.add_service(self.some_service, lambda data: data.copy())

    # ----- Runs in sequence -----

    def start(self):
        self.logger.info("start")

    def started(self):
        self.logger.info("started")

    def take(self, subscriptions):
        self.logger.info("take")

        self.some_stream = subscriptions[self.some_tag].get_stream()

        # if stream isn't supplied to robot and you still want subscriptions, make sure to call this
        self.some_stream.apply_subs()

    async def run(self):
        self.logger.info("run")

        # ----- utility methods -----

        # if subscription isn't required, check if this consumer stream has subscribed
        am_subscribed = self.is_subscribed(self.some_tag)
        self.logger.info(
            "I'm subscribed to %s: %s" % (self.some_tag, am_subscribed)
        )

        await asyncio.sleep(0.01)

        # since we returned None from time_started, we need to supply a start time manually
        self.start_time = time.time()

        await asyncio.sleep(0.01)

        current_time = self.dt()
        self.logger.info("Time since stream start is %0.4f" % current_time)

        await self.update()  # use this method if you choose. This isn't used by default

        self.exit()  # this is called when run exits. Call this or return from run to exit all streams

        self.is_running()  # use this in a while loop to keep streams running until one of them exits

    def stop(self):
        self.logger.info("stop")

    def stopped(self):
        self.logger.info("stopped")

    # ----- other overrideable methods -----

    async def update(self):
        self.logger.info("update")

    def time_started(self):
        # change the start time behavior. If you want the timer to start later, return None
        # and set self.start_time.
        return None

    def receive_log(self, log_level, message, line_info):
        # if LogParser subscribes to this stream, it will give log messages that match
        # this stream's name
        self.logger.info(message)


robot = Robot(write=False, log_level=20)

static = OrderDemoStatic()
asynchronous = OrderDemoAsync()
threaded = OrderDemoThreaded()

important_methods = ImportantMethods()
important_methods.subscribe(Subscription(important_methods.some_tag, DataStream()))

# robot.run(static)
# robot.run(asynchronous)
# robot.run(threaded)
robot.run(important_methods)