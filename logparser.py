import os
import re
import time
import datetime
import lzma as xz
import asyncio
from atlasbuggy.datastream import AsyncStream


class LogParser(AsyncStream):
    def __init__(self, file_name, directory, enabled=True, name=None, log_level=None, fps=None):
        self.pattern = re.compile(
            r"\[(?P<name>[a-zA-Z0-9]*) "
            r"@ (?P<filename>.*.py):"
            r"(?P<linenumber>[0-9]*)\]\["
            r"(?P<loglevel>[A-Z]*)\] "
            r"(?P<year>[0-9]*)-"
            r"(?P<month>[0-9]*)-"
            r"(?P<day>[0-9]*) "
            r"(?P<hour>[0-9]*):"
            r"(?P<minute>[0-9]*):"
            r"(?P<second>[0-9]*),"
            r"(?P<millisecond>[0-9]*): "
            r"(?P<message>.*)"
        )
        self.lines = []

        super(LogParser, self).__init__(enabled, name, log_level)

        self.file_name = file_name
        self.directory = directory
        self.full_path = os.path.join(self.directory, self.file_name)

        self.current_line = 0
        if self.enabled:
            with open(self.full_path, 'rb') as log_file:
                self.content = xz.decompress(log_file.read()).decode()
        else:
            self.content = ""

        self.line_info = dict(
            name="", filename="", linenumber=0, loglevel="",
            year=0, month=0, day=0, hour=0, minute=0, second=0, millisecond=0, timestamp=0,
            message="",
        )
        self.match = None
        self.line = ""
        if fps is None:
            self.delay = 0.0
        else:
            self.delay = 1 / fps

    async def run(self):
        matches = re.finditer(self.pattern, self.content)

        stream_names = {}
        for stream in self.streams.values():
            stream_names[stream.name] = stream

        for match_num, match in enumerate(matches):
            if not self.running():
                break
            self.line = match.group()
            self.current_line = match_num
            self.match = match

            for line_key, line_value in match.groupdict().items():
                # convert the matched element to the corresponding line_info's type
                # if line_info["year"] is of type int, convert the match to an int and assign the value to line_info
                self.line_info[line_key] = type(self.line_info[line_key])(line_value)

            self.line_info["timestamp"] = time.mktime(datetime.datetime(
                self.line_info["year"],
                self.line_info["month"],
                self.line_info["day"],
                self.line_info["hour"],
                self.line_info["minute"],
                self.line_info["second"],
                self.line_info["millisecond"]).timetuple())

            if self.line_info["name"] in stream_names:
                stream = stream_names[self.line_info["name"]]
                stream.receive_log(self.line_info["message"], self.line_info)

            await self.update()

    async def update(self):
        print(self.line_info)
        await asyncio.sleep(self.delay)


if __name__ == "__main__":
    import sys
    from atlasbuggy.robot import Robot


    def parse_file(file_name, directory):
        robot = Robot(wait_for_all=True, log_level=10)
        parser = LogParser(file_name, directory)
        robot.run(parser)


    parse_file(os.path.basename(sys.argv[1]), os.path.dirname(sys.argv[1]))
