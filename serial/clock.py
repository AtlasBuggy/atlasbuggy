"""
Keeps loops running at a consistent time. This class will notify you if the loop is falling behind
"""
import time
import asyncio


class Clock:
    def __init__(self, loops_per_second):
        """
        :param loops_per_second: similar to frames per second
        """
        self.loop_time = 0
        if loops_per_second is not None:
            self.seconds_per_loop = 1 / loops_per_second
        else:
            self.seconds_per_loop = None

        self.current_time = 0
        self.time_diff = 0
        self.offset = 0

        self.on_time = True

    def start(self, start_time=None):
        """
        Initialize the clock's time. start_time is used to provide a consist start time
        :param start_time:
        :return: None
        """
        if start_time is None:
            start_time = time.time()
        self.loop_time = start_time
        self.current_time = start_time

    def update(self):
        """
        pause the process if the elapsed time is greater than loops_per_second.
        :return: True if the process was paused. False if the loop ran too slowly
        """
        if self.seconds_per_loop is None:
            return True

        self.current_time = time.time()
        if self.current_time != self.loop_time:
            self.time_diff = self.current_time - self.loop_time
            self.offset = self.seconds_per_loop - self.time_diff

            if self.offset > 0:
                self.on_time = True
                time.sleep(self.offset)
            else:
                self.on_time = False

            self.loop_time = time.time()

            return self.offset > 0
        else:
            return False


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
    def __init__(self, delay_time):
        self.delay_time = delay_time
        self.prev_time = 0  # set later on just after being dequeued
        self.activated = False

    def update(self, timestamp=None):
        if timestamp is None:
            timestamp = time.time()
        if not self.activated and timestamp - self.prev_time > self.delay_time:
            self.activated = True
        return self.activated
