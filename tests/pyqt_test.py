from atlasbuggy import Orchestrator, Node, run
import asyncio

from PyQt5 import QtGui
from PyQt5.QtWidgets import QApplication, QWidget
import pyqtgraph as pyg

import numpy as np

class PlotViewer(QWidget):
    def __init__(self, size=(800,600), title='Plotter', ncols=2):
        super(PlotViewer, self).__init__();

        self.layout = None
        self.open = True
        self.ncols = ncols

        self.plot_widgets = {}

        # initialize QWidget and show
        self.init_ui(size, title)
        self.show()

    def init_ui(self, size, title):
        self.layout = QtGui.QGridLayout()
        self.setLayout(self.layout)
        self.resize(size[0], size[1])
        self.setWindowTitle(title)

    def add_plot(self, name, xlabel, ylabel):
        if name not in self.plot_widgets:
            widget = pyg.PlotWidget(title=name, labels={'left':xlabel, 'bottom':ylabel})
            self.plot_widgets[name] = widget
            self.add_widget(widget)

    def add_widget(self, widget):
        num_widgets = len(self.plot_widgets) - 1
        col = num_widgets % self.ncols
        row = int(num_widgets / self.ncols)
        self.layout.addWidget(widget, row, col)

    def plot(self, name, x, y, pen=None, symbol=None):
        if (symbol != None):
            self.plot_widgets[name].plot(x, y, pen=pen, symbol=symbol, clear=True)
        else:
            self.plot_widgets[name].plot(x, y, clear=True)

        QtGui.QApplication.processEvents()

    # overriding the default close event
    def closeEvent(self, event):
        self.open = False
        event.accept()

class PlotterNode(Node):
    def __init__(self, size=(800,600), title='Plotter', ncols=2, maximized=True):
        super(PlotterNode, self).__init__()

        self.running = True

        self.app = QApplication([])
        pyg.setConfigOption('background', 'w')
        pyg.setConfigOption('foreground', 'k')

        self.plotter = PlotViewer(size=size, title=title, ncols=ncols)

        if maximized:
            self.plotter.showMaximized()

    async def loop(self):
        while True:
            if not self.plotter.open:
                self.running = False

            if not self.running:
                return

            await asyncio.sleep(0.1)

    def add_plot(self, name, xlabel='X', ylabel='Y'):
        self.plotter.add_plot(name, xlabel, ylabel)

    def plot(self, name, x, y):
        self.plotter.plot(name, x, y, pen='r', symbol='o')

class DataNode(Node):
    def __init__(self, name):
        super(DataNode, self).__init__()

        self.plotter_tag = 'plotter'
        self.plotter_sub = self.define_subscription(self.plotter_tag)
        self.plotter = None

        self.plot_name = name

    async def setup(self):
        self.plotter.add_plot(self.plot_name)

    def take(self):
        self.plotter = self.plotter_sub.get_producer()

    async def loop(self):
        length = 1000
        while True:
            x = np.random.normal(size=length)
            y = np.random.normal(size=length)
            self.plotter.plot(self.plot_name, x, y)
            await asyncio.sleep(0.01)

class Plotter(Orchestrator):
    def __init__(self, event_loop):
        super(Plotter, self).__init__(event_loop)

        plotter_node = PlotterNode(
            title='good memes',
            size=(1000,1000),
            ncols=2
        )

        data_node1 = DataNode("plot1")
        data_node2 = DataNode("plot2")
        data_node3 = DataNode("plot3")
        data_node4 = DataNode("plot4")

        self.add_nodes(plotter_node, data_node1, data_node2, data_node3, data_node4)

        self.subscribe(plotter_node, data_node1, data_node1.plotter_tag)
        self.subscribe(plotter_node, data_node2, data_node2.plotter_tag)
        self.subscribe(plotter_node, data_node3, data_node3.plotter_tag)
        self.subscribe(plotter_node, data_node4, data_node4.plotter_tag)

run(Plotter)
