import time
import asyncio
from PyQt5 import QtGui
import pyqtgraph as pyg
from PyQt5.QtWidgets import QApplication, QWidget

from atlasbuggy import Node

from .messages import PlotMessage


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
            widget = pyg.PlotWidget(title=name, labels={'left': xlabel, 'bottom': ylabel})
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
    def __init__(self, enabled=True, size=(800, 600), title='Plotter', **kwargs):
        super(LivePlotter, self).__init__(enabled)

        self.size = size
        self.title = title
        self.plot_kwargs = kwargs
        self.app = None
        self.plotter = None

        self.plot_queues = {}
        self.plot_subs = {}
        self.plot_data = {}

        self.is_active = False

        self.init_plotter()

    def add_plot(self, plot_name, xlabel="X", ylabel="Y", **sub_kwargs):
        self.plotter.add_plot(plot_name, xlabel, ylabel)

        self.plot_subs[plot_name] = self.define_subscription(
            plot_name, message_type=PlotMessage, is_required=False, **sub_kwargs
        )
        self.plot_data[plot_name] = [[], []]

        return plot_name

    def take(self):
        for plot_name, plot_sub in self.plot_subs.items():
            self.plot_queues[plot_name] = plot_sub.get_queue()
            self.is_active = True

    def init_plotter(self):
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

            for plot_name, plot_queue in self.plot_queues.items():
                while not plot_queue.empty():
                    message = await plot_queue.get()
                    self.plot_data[plot_name][0].append(message.x_values)
                    self.plot_data[plot_name][1].append(message.y_values)

                    self.plotter.plot(plot_name, self.plot_data[plot_name][0], self.plot_data[plot_name][1],
                                      pen=message.pen, symbol=message.symbol)

            await asyncio.sleep(0.01)
