import time


class RecurringEvent:
    """
    Object used when linking recurring functions for a serial stream.
    """
    def __init__(self, repeat_time, current_time, function, args, include_event):
        """
        :param repeat_time: How often to call the passed function 
        :param current_time: The start time (in case this is being used in a simulated environment)
        :param function: a reference to a function. It doesn't take parameters by default. You can supply parameters
            with the args parameter
        :param args: Values to pass to the callback function
        :param include_event: If this is set to True, an instance of this event will be included. This is if you
            want to change the repeat time or arguments on the fly.
        """
        self.repeat_time = repeat_time
        self.function = function
        self.include_event = include_event
        self.args = args
        if current_time is None:
            self.prev_time = 0.0
        else:
            self.prev_time = current_time

    def update(self, timestamp):
        """
        Update this event with the current time. If appropriate, call the callback function 
        """
        if timestamp - self.prev_time > self.repeat_time:
            if self.include_event:
                self.function(self, *self.args)
            else:
                self.function(*self.args)
            self.prev_time = timestamp


class CommandPause:
    """
    This object is used space out commands. While paused, commands will continue to be queued up,
    they just won't get sent until this pause command has finished.
    """
    def __init__(self, delay_sec):
        """
        :param delay_sec: Amount of time to delay sending commands 
        """
        self.delay_time = delay_sec
        self.prev_time = 0  # set later on just after being dequeued
        self.activated = False

    def set_prev_time(self):
        """
        When the pause command emerges from the queue,
        SerialStream calls this method and starts checking if it has activated 
        """
        self.prev_time = time.time()

    def update(self, timestamp=None):
        """
        Update the pause command with the current time
        :return: True if the pause is finished
        """
        if timestamp is None:
            timestamp = time.time()
        if not self.activated and timestamp - self.prev_time > self.delay_time:
            self.activated = True
        return self.activated
