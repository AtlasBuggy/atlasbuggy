from atlasbuggy.plotters import LivePlotter
from atlasbuggy import Orchestrator, Node, run
import asyncio

import numpy as np

class DataNode(Node):
    def __init__(self, name):
        super(DataNode, self).__init__()

        self.plot_name = name

        self.plotter_tag = 'plotter'
        self.plotter_sub = self.define_subscription(self.plotter_tag)
        self.plotter = None

    async def setup(self):
        self.plotter.add_plot(self.plot_name)

    def take(self):
        self.plotter = self.plotter_sub.get_producer()

    async def loop(self):
        length = 100
        while True:
            x = np.random.normal(size=length)
            y = np.random.normal(size=length)
            self.plotter.plot(self.plot_name, x, y)
            await asyncio.sleep(0.01)

class Robot(Orchestrator):
    def __init__(self, event_loop):
        super(Robot, self).__init__(event_loop)

        plotter_node = LivePlotter(
            title='PLOTS',
            size=(1000,1000),
            ncols=2,
            frequency=0
        )

        data_node1 = DataNode("data1")

        self.add_nodes(plotter_node, data_node1)
        self.subscribe(plotter_node, data_node1, data_node1.plotter_tag)

run(Robot)
