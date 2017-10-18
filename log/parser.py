import re
import time
import logging
import datetime



class Line:
    def __init__(self):
        self.name = ""
        self.file_name = ""
        self.line_number = 0
        self.log_level_str = ""
        self.year = 0
        self.month = 0
        self.day = 0
        self.hour = 0
        self.minute = 0
        self.second = 0
        self.millisecond = 0

        self.timestamp = 0

        self.header_start = 0
        self.header_end = 0
        self.message = ""
        self.log_level = 0

        self.properties = [
            "name",
            "file_name",
            "line_number",
            "log_level_str",
            "year",
            "month",
            "day",
            "hour",
            "minute",
            "second",
            "millisecond",
        ]

        self.full = ""

    def calculate_timestamp(self):
        current_date = datetime.datetime(
            self.year, self.month, self.day, self.hour, self.minute, self.second, self.millisecond
        )
        self.timestamp = time.mktime(current_date.timetuple()) + current_date.microsecond / 1e3

    def __setitem__(self, key, value):
        name = self.properties[key]
        self.__dict__[name] = value

    def __getitem__(self, item):
        name = self.properties[item]
        return self.__dict__[name]


class LogParser:
    def __init__(self, log_contents: str):

        regex = r"\[(\w*) @ (\w.*):([0-9]*)\]\[(\w*)\] ([0-9]*)-([0-9]*)-([0-9]*) ([0-9]*):([0-9]*):([0-9]*),([0-9]*): "

        self.matches = re.finditer(regex, log_contents)
        self.lines = []
        self.start_time = None

        for match_num, match in enumerate(self.matches):
            line = Line()
            self.lines.append(line)

            for group_num in range(len(match.groups())):
                # using the default value for the line attribute, convert the matched group to the correct type
                line[group_num] = type(line[group_num])(match.group(group_num + 1))

            line.header_start = match.start()
            line.header_end = match.end()
            line.log_level = logging.getLevelName(line.log_level_str)
            line.full = match.group()

        for index in range(0, len(self.lines) - 1):
            self.extract_message(
                log_contents, self.lines[index],
                self.lines[index].header_end,
                self.lines[index + 1].header_start - 1
            )

        self.extract_message(
            log_contents, self.lines[-1],
            self.lines[-1].header_end,
            len(log_contents) - 1
        )

        self.current_index = 0

    def append_log(self, parser, sort=True):
        if parser is not None:
            self.lines.extend(parser.lines)
            if sort:
                self.sort()

    def extract_message(self, log_contents, line, start_index, end_index):
        message = log_contents[start_index: end_index]
        line.message = message
        line.full += message
        line.calculate_timestamp()
        if self.start_time is None:
            self.start_time = line.timestamp

    def sort(self, line_property="timestamp"):
        def _line_sort_fn(element):
            return element[line_property]

        self.lines.sort(key=_line_sort_fn)

    def __next__(self):
        if self.current_index == len(self.lines):
            self.current_index = 0
            raise StopIteration

        line = self.lines[self.current_index]
        self.current_index += 1
        return line

    def __iter__(self):
        return self

    def skip(self):
        self.current_index -= 1

    def current_time(self):
        if self.current_index >= len(self.lines):
            current_index = len(self.lines) - 1
        else:
            current_index = self.current_index
        return self.lines[current_index].timestamp - self.start_time

    def delta_t(self):
        current_index = self.current_index - 1
        if current_index < len(self.lines) - 1:
            next_t = self.lines[current_index + 1].timestamp
            current_t = self.lines[current_index].timestamp

            return next_t - current_t
        else:
            return 0

