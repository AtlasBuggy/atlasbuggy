import re
import time


class Message:
    message_regex = r"Message\(t=(\d.*), n=(\d*)\)"

    def __init__(self, timestamp=None, n=0, name=None):
        if timestamp is None:
            self.timestamp = time.time()
        else:
            self.timestamp = timestamp
        self.n = n
        self._name = name

    @classmethod
    def parse(cls, message):
        match = re.match(cls.message_regex, message)
        if match is not None:
            message_time = float(match.group(1))
            n = int(match.group(2))

            return Message(message_time, n)
        else:
            return None

    @property
    def name(self):
        if not hasattr(self, "_name") or self._name is None:
            return self.__class__.__name__
        else:
            return self._name

    def __str__(self):
        return "%s(t=%s, n=%s)" % (self.name, self.timestamp, self.n)
