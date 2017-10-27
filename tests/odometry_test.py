import time

from atlasbuggy import Orchestrator, Node, Message, run
from atlasbuggy.plotter import LivePlotter

class OdometryMessage(Message):
    def __init__(self, timestamp, n, x, y):
        self.timestamp = timestamp
        self.x = x
        self.y = y
        super(OdometryMessage, self).__init__(timestamp, n)

class Odometry(Node):
    # TODO: correctly fill out these values
    wheel_width = 10 # wheel width in meters
    ticks_per_rev = 60
    wheel_radius = 40 # wheel radius in meters

    def __init__(self):
        super(Odometry, self).__init__()

        self.imu_tag = 'imu'
        self.imu_sub = self.define_subscription(self.imu_tag)
        self.imu_queue = None
        self.imu = None

        self.encoder_tag = 'encoder'
        self.encoder_sub = self.define_subscription(self.encoder_tag)
        self.encoder_queue = None

        self.prev_imu_t = None
        self.prev_enc_t = None

        self.x = 0
        self.y = 0

        self.start_heading = 0.1 # TODO: get start heading

    def take(self):
        self.imu_queue = self.imu_sub.get_queue()
        self.imu = self.imu_sub.get_producer()
        self.encoder_queue = self.encoder_sub.get_queue()

    async def loop(self):
        counter = 0
        while True:
            # initialize time if not initialized
            if self.prev_t == None:
                self.prev_t = time.time()

            # wait for new encoder data
            if self.encoder_queue.empty()
                await asyncio.sleep(0.0)
                continue

            # get left wheel velocity from encoders
            encoder_msg = await self.encoder_queue.get()
            vel_l = self.enc_to_vel(encoder_msg)

            # get angular velocity from imu
            imu_msg = await self.imu_queue.get()
            heading = 0.5 # TODO: get current heading and convert to radians
            ang_v = self.imu_to_w(imu_msg) # should have IMU message

            dt = 0.01 # TODO: get least dt between encoder and imu

            # calculate linear velocity and angular velocity
            vel_r = ang_v * Odometry.wheel_width + vel_l
            lin_v = (vel_l + vel_r)/2

            # update x and y position with Dead Reckoning
            dx = lin_v * dt * cos(heading)
            dy = lin_v * dt * sin(heading)
            self.x += dx
            self.y += dy

            timestamp = time.time()
            counter += 1

            msg = OdometryMessage(timestamp, counter, self.x, self.y)
            await self.broadcast(msg)

    # TODO: write function that converts encoder reading to velocity
    def enc_to_vel(self, encoder_msg):
        pass

    # TODO: write function that converts imu message to angular velocity
    def imu_to_w(self, imu_msg):
        pass

class OdometryPlot(Node):
    def __init__(self):
        super(OdometryPlot, self).__init__()

        self.plotter_tag = 'plotter'
        self.plotter_sub = self.define_subscription(self.plotter_tag)
        self.plotter = None

        self.odom_tag = 'odometry'
        self.odom_sub = self.define_subscription(self.odom_tag)
        self.odom_queue = None

        self.x = []
        self.y = []

    def take(self):
        self.plotter = self.plotter_sub.get_producer()
        self.odom_queue = self.odom_sub.get_queue()

    async def setup(self):
        self.plotter.add_plot('Odometry', xlabel='X(m)', ylabel='Y(m)')

    async def loop(self):
        while True:
            if self.odom_queue.empty():
                await asyncio.sleep(0.0)
                continue

            odom = await self.odom_queue.get()
            self.x.append(odom.x)
            self.y.append(odom.y)

            self.plotter.plot('Odometry', self.x, self.y)

class Robot(Orchestrator):
    def __init__(self, event_loop):
        super(Robot, self).__init__(event_loop)

        imu_node = None
        encoder_node = None
        live_plotter = LivePlotter(
            title='Odometry Data',
            maximized=True
        )
        odom = Odometry()
        odom_plot = OdometryPlot()

        self.add_nodes(imu_node, encoder_node, live_plotter, odom, odom_plot)

        self.subscribe(imu_node, odom, odom.imu_tag)
        self.subscribe(encoder_node, odom, odom.encoder_tag)
        self.subscribe(live_plotter, odom_plot, odom_plot.plotter_tag)
        self.subscribe(odom, odom_plot, odom_plot.odom_tag)

run(Robot)