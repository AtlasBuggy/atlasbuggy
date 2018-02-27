import re
import time
import datetime

with open("logs/2017_Oct_17/ImmutableConsumer/19_57_14.log") as log_file:
    contents1 = log_file.read()
# coding=utf8
# the above tag defines encoding for this document and is for Python 2.x compatibility

regex = r"\[(\w*) @ (\w.*):([0-9]*)\]\[(\w*)\] ([0-9]*)-([0-9]*)-([0-9]*) ([0-9]*):([0-9]*):([0-9]*),([0-9]*): "

matches = re.finditer(regex, contents1)

lines = []


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

        self.properties = [
            self.name,
            self.file_name,
            self.line_number,
            self.log_level_str,
            self.year,
            self.month,
            self.day,
            self.hour,
            self.minute,
            self.second,
            self.millisecond
        ]

        self.timestamp = 0

        self.header_start = 0
        self.header_end = 0
        self.message = ""

def calculate_timestamp(self):
    current_date = datetime.datetime(
        self.year, self.month, self.day, self.hour, self.minute, self.second, self.millisecond
    )
    self.timestamp = time.mktime(current_date.timetuple()) + current_date.microsecond / 1e3

for match_num, match in enumerate(matches):
    line = Line()
    lines.append(line)

    for group_num in range(len(match.groups())):
        line.properties[group_num] = match.group(group_num + 1)
    # line.name = match.group(1)
    # line.file_name = match.group(2)
    # line.line_number = match.group(3)
    # line.log_level_str = match.group(4)
    # line.year = match.group(5)
    # line.month = match.group(6)
    # line.day = match.group(7)
    # line.hour = match.group(8)
    # line.minute = match.group(9)
    # line.second = match.group(10)
    # line.millisecond = match.group(11)

    line.header_start = match.start()
    line.header_end = match.end()

for index in range(1, len(lines)):
    message = contents1[
              lines[index - 1].header_end:
              lines[index].header_start - 1
              ]
    lines[index].message = message
    lines[index].calculate_timestamp()
    print(repr(message), lines[index].timestamp)
