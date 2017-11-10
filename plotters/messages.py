from atlasbuggy import Message


class PlotMessage(Message):
    def __init__(self, x_values, y_values, pen=None, symbol='o'):
        super(PlotMessage, self).__init__()
        self.x_values = x_values
        self.y_values = y_values
        self.pen = pen
        self.symbol = symbol
