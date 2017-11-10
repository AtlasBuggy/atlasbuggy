import asyncio
import time

from atlasbuggy import Node, Message

from PyQt5 import QtGui
from PyQt5.QtWidgets import QApplication, QWidget
import pyqtgraph as pyg


class PlotViewer(QWidget):
    def __init__(self, size=(800, 600), title='Plotter', **kwargs):
        super(PlotViewer, self).__init__()

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


class PlotMessage(Message):
    def __init__(self, plot_name, x_values, y_values, pen=None, symbol='o'):
        self.plot_name = plot_name
        self.x_values = x_values
        self.y_values = y_values
        self.pen = pen
        self.symbol = symbol


class PlotConfigMessage(Message):
    def __init__(self, plot_name, x_label="X", y_label="Y"):
        self.plot_name = plot_name
        self.x_label = x_label
        self.y_label = y_label


class LivePlotter(Node):
    def __init__(self, enabled=True, size=(800, 600), title='Plotter', **kwargs):
        super(LivePlotter, self).__init__(enabled)

        self.size = size
        self.title = title
        self.plot_kwargs = kwargs
        self.app = None
        self.plotter = None

        self.plots = {}

        self.xy_tag = "xy"
        self.xy_sub = self.define_subscription(self.xy_tag, message_type=PlotMessage, is_required=False)
        self.xy_queue = None

        self.is_active = False

    def take(self):
        if self.is_subscribed(self.xy_queue):
            self.xy_queue = self.xy_queue.get_queue()
            self.is_active = True

    async def setup(self):
        size = self.plot_kwargs.get('size', self.size)
        title = self.plot_kwargs.get('title', self.title)
        maximized = self.plot_kwargs.get('maximized', False)

        self.app = QApplication([])
        pyg.setConfigOption('background', 'w')
        pyg.setConfigOption('foreground', 'k')

        self.plotter = PlotViewer(size=size, title=title, **self.plot_kwargs)

        if maximized:
            self.plotter.showMaximized()

    async def loop(self):
        if not self.is_active:
            return
        while True:
            if not self.plotter.open:
                return

            if self.is_subscribed(self.xy_queue):
                while not self.xy_queue.empty():
                    message = await self.xy_queue.get()
                    if isinstance(message, PlotMessage):
                        self.plotter.plot(message.plot_name, message.x_label, message.y_label, pen=message.pen, symbol=message.symbol)

                    elif isinstance(message, PlotConfigMessage):
                        self.plotter.add_plot(message.plot_name, message.xlabel, message.ylabel)

            await asyncio.sleep(0.01)
