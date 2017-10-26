import asyncio
import time

from atlasbuggy import Orchestrator, Node, run

from PyQt5 import QtGui
from PyQt5.QtWidgets import QApplication, QWidget
import pyqtgraph as pyg

class PlotViewer(QWidget):
    def __init__(self, size=(800,600), title='Plotter', **kwargs):
        super(PlotViewer, self).__init__();

        self.open = True
        self.layout = None
        self.ncols = kwargs.get('ncols', 2)
        self.frequency = kwargs.get('frequency', 0)

        self.last_t = time.time()

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
            plot = widget.getPlotItem()
            
            self.plot_widgets[name] = widget
            self.add_widget(widget)

    def add_widget(self, widget):
        num_widgets = len(self.plot_widgets) - 1
        col = num_widgets % self.ncols
        row = int(num_widgets / self.ncols)
        self.layout.addWidget(widget, row, col)

    def plot(self, name, x, y, pen=None, symbol=None):
        # wait to change the frequency
        while (time.time() - self.last_t) < self.frequency:
            continue

        self.last_t = time.time()

        if (symbol != None):
            self.plot_widgets[name].plot(x, y, pen=pen, symbol=symbol, clear=True, symbolSize=2)
        else:
            self.plot_widgets[name].plot(x, y, clear=True, symbolSize=2)

        QtGui.QApplication.processEvents()

    # overriding the default close event
    def closeEvent(self, event):
        self.open = False
        event.accept()

class LivePlotter(Node):
    def __init__(self, size=(800,600), title='Plotter', **kwargs):
        super(LivePlotter, self).__init__()

        size = kwargs.get('size', (800,600))
        title = kwargs.get('title', 'Plotter')
        maximized = kwargs.get('maximized', False)

        self.app = QApplication([])
        pyg.setConfigOption('background', 'w')
        pyg.setConfigOption('foreground', 'k')

        self.plotter = PlotViewer(size=size, title=title, **kwargs)

        if maximized:
            self.plotter.showMaximized()

    async def loop(self):
        while True:
            if not self.plotter.open:
                return

            await asyncio.sleep(0.1)

    def add_plot(self, name, xlabel='X', ylabel='Y'):
        self.plotter.add_plot(name, xlabel, ylabel)

    def plot(self, name, x, y):
        self.plotter.plot(name, x, y, pen=None, symbol='o')
        # self.plotter.plot(name, x, y)