import os
import re
import time
import datetime
import lzma as xz
import asyncio
from atlasbuggy.datastream import AsyncStream


class LogParser(AsyncStream):
    def __init__(self, file_name, directory="", enabled=True, name=None, log_level=None, fps=None):
        # regex string code. Logs follow a certain format. Parse out these pieces of info.
        self.pattern = re.compile(
            r"(?P<name>[a-zA-Z0-9]*) @ "
            r"(?P<filename>.*\.py):"
            r"(?P<linenumber>[0-9]*)\]\["
            r"(?P<loglevel>[A-Z]*)\] "
            r"(?P<year>[0-9]*)-"
            r"(?P<month>[0-9]*)-"
            r"(?P<day>[0-9]*) "
            r"(?P<hour>[0-9]*):"
            r"(?P<minute>[0-9]*):"
            r"(?P<second>[0-9]*),"
            r"(?P<millisecond>[0-9]*): "
            r"(?P<message>([.\S\s]+?(\n\[)))"
        )

        super(LogParser, self).__init__(enabled, name, log_level)

        # info about the log file path
        self.file_name = file_name
        self.directory = directory
        self.full_path = os.path.join(self.directory, self.file_name)

        # current line of the log we're on
        self.line_number = 0
        self.line = ""

        # decompress the log file
        if self.enabled:
            with open(self.full_path, 'rb') as log_file:
                self.content = xz.decompress(log_file.read()).decode()
        else:
            self.content = ""

        # all pieces information in each line
        self.line_info = dict(
            name="", filename="", linenumber=0, loglevel="",
            year=0, month=0, day=0, hour=0, minute=0, second=0, millisecond=0, timestamp=0,
            message="",
        )

        # How fast the log parser should run at
        if fps is None:
            self.delay = 0.0
        else:
            self.delay = 1 / fps

    async def run(self):
        # find all matches in the log
        matches = re.finditer(self.pattern, self.content)

        # index streams by their names instead of the key word they were assigned in self.give
        stream_names = {}
        for stream in self.streams.values():
            stream_names[stream.name] = stream

        for match_num, match in enumerate(matches):
            if not self.running():
                break
            self.line_number = match_num

            for line_key, line_value in match.groupdict().items():
                # convert the matched element to the corresponding line_info's type
                # if line_info["year"] is of type int, convert the match to an int and assign the value to line_info
                self.line_info[line_key] = type(self.line_info[line_key])(line_value)

            line = match.group()
            self.line = (line[-1] + line[:-1]).strip("\n")
            self.line_info["message"] = self.line_info["message"][:-1].strip("\n")

            # make timestamp from unix epoch
            self.line_info["timestamp"] = time.mktime(datetime.datetime(
                self.line_info["year"],
                self.line_info["month"],
                self.line_info["day"],
                self.line_info["hour"],
                self.line_info["minute"],
                self.line_info["second"],
                self.line_info["millisecond"]).timetuple())

            # notify stream if its name is found in the log
            if self.line_info["name"] in stream_names:
                stream = stream_names[self.line_info["name"]]
                stream.receive_log(self.line_info["loglevel"], self.line_info["message"], self.line_info)

            await self.update()

    async def update(self):
        await asyncio.sleep(self.delay)


if __name__ == "__main__":
    import sys
    from atlasbuggy.robot import Robot


    class DemoParser(LogParser):
        def __init__(self, file_name, directory):
            super(DemoParser, self).__init__(file_name, directory)

        async def update(self):
            print("\t'%s'" % self.line)
            # print(self.line_info)
            await asyncio.sleep(self.delay)


    def parse_file(file_name, directory):
        if len(sys.argv) > 1:
            robot = Robot(wait_for_all=True, log_level=10)
            parser = DemoParser(file_name, directory)
            robot.run(parser)
        else:
            raise RuntimeError("Please input the file path you want to display")


    def compress_file(file_name, directory):
        full_path = os.path.join(directory, file_name)
        with open(full_path, "r") as log, open(full_path + ".xz", "wb") as out:
            out.write(xz.compress(log.read().encode()))


    _input_file_name = os.path.basename(sys.argv[1])
    _input_dir_name = os.path.dirname(sys.argv[1])

    if _input_file_name.endswith(".log"):
        compress_file(_input_file_name, _input_dir_name)
    else:
        parse_file(_input_file_name, _input_dir_name)
