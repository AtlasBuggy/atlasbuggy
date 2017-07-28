import os
import re
import time
import datetime
import lzma as xz
import asyncio
from .datastream import AsyncStream


class LogParser(AsyncStream):
    """
    Parse a log file to simulate how the robot behaved that day
    """

    def __init__(self, file_name, directory="", enabled=True, name=None, log_level=None, update_rate=0.0):
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

        super(LogParser, self).__init__(enabled, log_level, name)

        # info about the log file path
        self.file_name = file_name
        self.directory = directory
        self.full_path = os.path.join(self.directory, self.file_name)

        self.logged_streams = {}

        # current line of the log we're on
        self.line_number = 0
        self.line = ""

        self.prev_time = None
        self.update_rate = update_rate

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

    def take(self, subscriptions):
        """
        Listen for subscriptions in log file
        
        DO NOT override this method. Use take_from_log instead
        """
        for subscription in subscriptions.values():
            stream = subscription.producer_stream
            self.logged_streams[stream.name] = stream

        self.take_from_log(subscriptions)
    
    def take_from_log(self, subscriptions):
        pass
    
    def start(self):
        for stream in self.logged_streams.values():
            stream.check_subscriptions()
            stream.take(stream.subscriptions)

    async def run(self):
        # find all matches in the log
        matches = re.finditer(self.pattern, self.content)

        for match_num, match in enumerate(matches):
            if not self.is_running():
                break
            self.line_number = match_num

            for line_key, line_value in match.groupdict().items():
                # convert the matched element to the corresponding line_info's type
                # if line_info["year"] is of type int, convert the match to an int and assign the value to line_info
                self.line_info[line_key] = type(self.line_info[line_key])(line_value)

            # a quirk of the way I'm parsing with regex. Move the last character of the message to the beginning and
            # remove trailing newlines
            line = match.group()
            self.line = (line[-1] + line[:-1]).strip("\n")
            self.line_info["message"] = self.line_info["message"][:-1].strip("\n")

            # under scrutiny, not sure what this was for
            # if self.prev_time is not None:
            #     self.prev_time = self.line_info["timestamp"]

            # create a unix timestamp using the date
            current_date = datetime.datetime(
                self.line_info["year"],
                self.line_info["month"],
                self.line_info["day"],
                self.line_info["hour"],
                self.line_info["minute"],
                self.line_info["second"],
                self.line_info["millisecond"])

            # make timestamp from unix epoch
            self.line_info["timestamp"] = time.mktime(current_date.timetuple()) + current_date.microsecond / 1e6

            # notify stream if its name is found in the log
            if self.line_info["name"] in self.logged_streams:
                stream = self.logged_streams[self.line_info["name"]]
                stream.receive_log(self.line_info["loglevel"], self.line_info["message"], self.line_info)

            # call subclass's update
            await self.update()

            self.prev_time = self.line_info["timestamp"]

    def time_diff(self):
        """
        Get time since the last log message
        :return: 0.0 if no log messages have been received yet
        """
        if self.prev_time is None:
            return 0.0
        else:
            return self.line_info["timestamp"] - self.prev_time

    async def update(self):
        await asyncio.sleep(self.update_rate)


if __name__ == "__main__":
    import sys
    from atlasbuggy.robot import Robot


    class DemoParser(LogParser):
        def __init__(self, file_name, directory):
            super(DemoParser, self).__init__(file_name, directory)

        async def update(self):
            print("\t'%s'" % self.line)
            # print(self.line_info)
            await asyncio.sleep(0.0)


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
