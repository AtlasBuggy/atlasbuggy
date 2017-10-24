import re
import time


class Message:
    message_regex = r"Message\(t=(\d.*), n=(\d*)\)"

    def __init__(self, timestamp=None, n=0):
        if timestamp is None:
            self.timestamp = time.time()
        else:
            self.timestamp = timestamp
        self.n = n

    @classmethod
    def parse(clc, message):
        match = re.match(clc.message_regex, message)
        if match is not None:
            message_time = float(match.group(1))
            n = int(match.group(2))

            return Message(message_time, n)
        else:
            return None

    def __str__(self):
        return "%s(t=%s, n=%s)" % (self.__class__.__name__, self.timestamp, self.n)
