import sys
import asyncio
import traceback
from ..datastream import AsyncStream


class CommandLine(AsyncStream):
    def __init__(self, enabled=True, log_level=None, prompt_text=">> ", name=None):
        super(CommandLine, self).__init__(enabled, log_level, name)
        self.prompt_text = prompt_text
        self.queue = asyncio.Queue()

    def start(self):
        self.asyncio_loop.add_reader(sys.stdin, self.handle_stdin)

    def handle_stdin(self):
        data = sys.stdin.readline()
        asyncio.async(self.queue.put(data))

    async def run(self):
        while self.is_running():
            print("\r%s" % self.prompt_text, end="")
            data = await self.queue.get()
            try:
                self.handle_input(data.strip('\n'))
            except BaseException as error:
                traceback.print_exc()
                print(error)
                self.logger.warning("Failed to parse input: " + repr(data))

    def handle_input(self, line):
        if line == 'q':
            self.exit()
