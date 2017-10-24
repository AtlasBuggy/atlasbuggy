import re
import copy
import time
import logging
import datetime

from . import default


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
        self.microsecond = 0

        self.timestamp = 0

        self.header_start = 0
        self.header_end = 0
        self.message = ""
        self.log_level = 0

        self.is_part_of_buffer = False

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
            "microsecond",
        ]

        self.full = ""

    def calculate_timestamp(self):
        current_date = datetime.datetime(
            self.year, self.month, self.day, self.hour, self.minute, self.second, self.microsecond
        )
        self.timestamp = time.mktime(current_date.timetuple()) + current_date.microsecond / 1e3

    def __setitem__(self, key, value):
        if type(key) == int:
            key = self.properties[key]
        self.__dict__[key] = value

    def __getitem__(self, item):
        if type(item) == int:
            item = self.properties[item]

        return self.__dict__[item]

    def __cmp__(self, other):
        return copy.copy(self, other)


class LogParser:
    def __init__(self, log_contents: str):

        regex = r"\[(\w*) @ (\w.*):([0-9]*)\]\[(\w*)\] ([0-9]*)-([0-9]*)-([0-9]*) ([0-9]*):([0-9]*):([0-9]*),([0-9]*): "
        self.buffer_regex = r"\[(\S*), (\d.*)\]: "

        self.matches = re.finditer(regex, log_contents)
        self.lines = []
        self.start_time = None
        self.current_index = 0

        self._resort_by_time = False

        for match_num, match in enumerate(self.matches):
            line = self.parse_line(match_num, match)
            self.lines.append(line)

        all_buffer_lines = []
        for index in range(0, len(self.lines) - 1):
            buffer_lines = self.extract_message(
                log_contents, self.lines[index],
                self.lines[index].header_end,
                self.lines[index + 1].header_start - 1
            )
            if len(buffer_lines) > 0:
                all_buffer_lines.extend(buffer_lines)

        buffer_lines = self.extract_message(
            log_contents, self.lines[-1],
            self.lines[-1].header_end,
            len(log_contents) - 1
        )
        if len(buffer_lines):
            all_buffer_lines.extend(buffer_lines)

        self.lines.extend(all_buffer_lines)

        if self._resort_by_time:
            self.sort()

    def parse_line(self, match_num, match):
        line = Line()
        for group_num in range(len(match.groups())):
            # using the default value for the line attribute, convert the matched group to the correct type
            line[group_num] = type(line[group_num])(match.group(group_num + 1))

        line.header_start = match.start()
        line.header_end = match.end()
        line.log_level = logging.getLevelName(line.log_level_str)
        line.line_number = match_num
        line.full = match.group()

        return line

    def parse_buffer_line(self, line, match):
        buffer_line = copy.copy(line)

        buffer_line.log_level_str = match.group(1)
        buffer_line.log_level = logging.getLevelName(match.group(1))
        buffer_line.timestamp = float(match.group(2))

        date = datetime.datetime.fromtimestamp(buffer_line.timestamp)

        buffer_line.year = date.year
        buffer_line.month = date.month
        buffer_line.day = date.day
        buffer_line.hour = date.hour
        buffer_line.minute = date.minute
        buffer_line.second = date.second
        buffer_line.microsecond = date.microsecond

        buffer_line.header_start = match.start()
        buffer_line.header_end = match.end()
        buffer_line.full = match.group()

        buffer_line.is_part_of_buffer = True

        return buffer_line

    def extract_buffer_message(self, buffer_contents, buffer_line, start_index, end_index):
        message = buffer_contents[start_index: end_index]
        buffer_line.message = message
        buffer_line.full += message

    def extract_message(self, log_contents, line, start_index, end_index):
        message = log_contents[start_index: end_index]
        line.calculate_timestamp()
        if self.start_time is None:
            self.start_time = line.timestamp
        line.message = message

        buffer_lines = []
        if default.log_buffer_start in message:
            self._resort_by_time = True

            buffer_matches = re.finditer(self.buffer_regex, message)

            for match in buffer_matches:
                buffer_line = self.parse_buffer_line(line, match)

                buffer_lines.append(buffer_line)

            for index in range(len(buffer_lines) - 1):
                self.extract_buffer_message(
                    message,
                    buffer_lines[index],
                    buffer_lines[index].header_end,
                    buffer_lines[index + 1].header_start - 1
                )

            self.extract_buffer_message(
                message,
                buffer_lines[-1],
                buffer_lines[-1].header_end,
                len(message) - 1
            )
        else:
            line.full += message

        return buffer_lines

    def append_log(self, parser, sort=True):
        if parser is not None:
            self.lines.extend(parser.lines)
            if sort:
                self.sort()

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
