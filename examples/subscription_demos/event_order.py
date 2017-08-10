import asyncio
from atlasbuggy import DataStream, AsyncStream, ThreadedStream, Robot


class OrderDemoStatic(DataStream):
    def start(self):
        self.logger.info("start")

    def started(self):
        self.logger.info("started")

    def take(self, subscriptions):
        self.logger.info("take")

    def run(self):
        self.logger.info("run")

    def stop(self):
        self.logger.info("stop")

    def stopped(self):
        self.logger.info("stopped")


class OrderDemoAsync(AsyncStream):
    def start(self):
        self.logger.info("start")

    def started(self):
        self.logger.info("started")

    def take(self, subscriptions):
        self.logger.info("take")

    async def run(self):
        self.logger.info("run")
        await asyncio.sleep(0.0)

    def stop(self):
        self.logger.info("stop")

    def stopped(self):
        self.logger.info("stopped")


class OrderDemoThreaded(ThreadedStream):
    def start(self):
        self.logger.info("start")

    def started(self):
        self.logger.info("started")

    def take(self, subscriptions):
        self.logger.info("take")

    def run(self):
        self.logger.info("run")

    def stop(self):
        self.logger.info("stop")

    def stopped(self):
        self.logger.info("stopped")


class ImportantMethods(ThreadedStream):

    # methods to not override:
    #   dt, subscribe, require_subscription, adjust_subscription, post, add_service, is_running, apply_subs,
    #   has_started, has_stopped, exit

    def __init__(self):
        super(ImportantMethods, self).__init__()

        # init methods

        self.some_subscription = "something"
        self.require_subscription(self.some_subscription)

        self.adjust_subscription(
            self.some_subscription,
            # change properties of some_subscription
        )

        self.some_service = "new_service"
        self.add_service(self.some_service, lambda data: data.copy())

    # Runs in sequence

    def start(self):
        self.logger.info("start")

    def started(self):
        self.logger.info("started")

    def take(self, subscriptions):
        self.logger.info("take")

        # if stream isn't supplied to robot and you still want subscriptions, make sure to call this
        self.apply_subs()

    def run(self):
        self.logger.info("run")

        # utility methods

        # if subscription isn't required, check if this consumer stream has subscribed
        am_subscribed = self.is_subscribed(self.some_subscription)
        self.logger.info(
            "I'm subscribed to %s: %s" % (self.some_subscription, am_subscribed)
        )

        current_time = self.dt()
        self.logger.info("Time since stream start is %0.4f" % current_time)

        self.update()  # use this method if you choose. This isn't used by default

        self.exit()  # this is called when run exits. Call this or return from run to exit all streams

        self.is_running()  # use this in a while loop to keep streams running until one of them exits

    def stop(self):
        self.logger.info("stop")

    def stopped(self):
        self.logger.info("stopped")

    # overrideable methods

    def update(self):
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

robot.run(static)
# robot.run(asynchronous)
# robot.run(threaded)
