import time


class RecurringEvent:
    def __init__(self, repeat_time, current_time, function, args, include_event):
        self.repeat_time = repeat_time
        self.function = function
        self.include_event = include_event
        self.args = args
        if current_time is None:
            self.prev_time = 0.0
        else:
            self.prev_time = current_time

    def update(self, timestamp):
        if timestamp - self.prev_time > self.repeat_time:
            if self.include_event:
                self.function(self, *self.args)
            else:
                self.function(*self.args)
            self.prev_time = timestamp


class CommandPause:
    def __init__(self, delay_sec):
        self.delay_time = delay_sec
        self.prev_time = 0  # set later on just after being dequeued
        self.activated = False

    def update(self, timestamp=None):
        if timestamp is None:
            timestamp = time.time()
        if not self.activated and timestamp - self.prev_time > self.delay_time:
            self.activated = True
        return self.activated
