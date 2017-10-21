import sys
import time
import numpy as np

from PyQt5 import QtGui
from PyQt5.QtWidgets import QApplication, QWidget
import pyqtgraph as pyg

import asyncio
from atlasbuggy import Orchestrator, Node, run

class PlotViewer(QWidget):
    def __init__(self, size=(800,600), title='Plotter'):
        super(PlotViewer, self).__init__();

        self.layout = None
        self.plot_widget = pyg.PlotWidget()

        self.init_ui(size, title)
        self.add_widgets(self.plot_widget)
        self.show()

    def init_ui(self, size, title):
        self.layout = QtGui.QGridLayout()
        self.setLayout(self.layout)
        self.resize(size[0], size[1])
        self.setWindowTitle(title)

    def add_widgets(self, *widgets):
        for i, widget in enumerate(widgets):
            self.layout.addWidget(widget, 0, i)

    def plot(self, x, y, pen=None, symbol=None):
        if (symbol != None):
            self.plot_widget.plot(x, y, pen=pen, symbol=symbol, clear=True)
        else:
            self.plot_widget.plot(x, y, clear=True)

        QtGui.QApplication.processEvents()

class PlotterNode(Node):
    def __init__(self):
        super(PlotterNode, self).__init__()

        self.running = True
        self.app = QApplication([])
        self.plotter = PlotViewer()

    async def loop(self):
        while True:
            if(self.app.exec_() == 0):
                self.running = False

            if(self.running):
                x = np.random.normal(size=1000)
                y = np.random.normal(size=1000)
                self.plot(self.plotter, x, y)

            await asyncio.sleep(1)

    def plot(self, plotter, x, y):
        plotter.plot(x, y)

class Plotter(Orchestrator):
    def __init__(self, event_loop):
        super(Plotter, self).__init__(event_loop)

        self.plotter_node = PlotterNode()
        self.add_nodes(self.plotter_node)

    async def loop(self):
        while True:
            if not self.plotter_node.running:
                return
            await asyncio.sleep(0.5)

run(Plotter)
