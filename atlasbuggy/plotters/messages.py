from atlasbuggy import Message


class PlotMessage(Message):
    APPEND = 0
    EXTEND = 1
    OVERRIDE = 2

    def __init__(self, x_values, y_values, pen=None, symbol='o', option=0):
        super(PlotMessage, self).__init__()
        self.x_values = x_values
        self.y_values = y_values
        self.pen = pen
        self.symbol = symbol
        self.option = option
