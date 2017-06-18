import asyncio
from atlasbuggy.datastream import AsyncStream


class SocketClient(AsyncStream):
    def __init__(self, name, host, port=5001, enabled=True, log_level=None, timeout=None):
        super(SocketClient, self).__init__(enabled, name, log_level)
        self.host = host
        self.port = port
        self.timeout = timeout

        self.reader = None
        self.writer = None

    async def run(self):
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
        self.logger.debug("Connection opened with %s:%s" % (self.host, self.port))
        try:
            self.write(self.name + "\n")
            while self.all_running():
                if self.timeout:
                    data = await self.reader.readline()
                else:
                    data = await asyncio.wait_for(self.reader.readline(), timeout=self.timeout)

                self.received(data)

                if data is None or len(data) == 0:
                    self.logger.warning("socket received nothing")
                    self.exit()
                    return
        finally:
            # self.debug_print("Disconnecting from %s %d", self.host, self.port)
            # self.writer.close()
            self.logger.debug("Disconnected from %s %d" % (self.host, self.port))

    def write(self, data):
        if self.writer is None:
            raise Exception("async socket not started!")
        data += "\n"
        self.writer.write(data.encode())

    def write_eof(self):
        self.writer.write_eof()

    def received(self, data):
        pass


class SocketServer(AsyncStream):
    def __init__(self, enabled=True, log_level=None, name=None, host='0.0.0.0', port=5001, timeout=None):
        super(SocketServer, self).__init__(enabled, name, log_level)

        self.host = host
        self.port = port
        self.timeout = timeout

        self.clients = []
        self.client_tasks = {}
        self.client_writers = {}

    async def run(self):
        self.logger.debug("Starting server on %s:%s" % (self.host, self.port))
        await asyncio.start_server(self.accept_client, host=self.host, port=self.port)
        while self.running():
            await asyncio.sleep(0.5)

    def accept_client(self, client_reader, client_writer):
        task = asyncio.Task(self.handle_client(client_reader, client_writer, len(self.clients)))
        self.clients.append((client_reader, client_writer))
        self.client_tasks[task] = client_writer

        def client_done(end_task):
            del self.client_tasks[end_task]
            client_writer.stop()
            self.logger.debug("ending connection")

        task.add_done_callback(client_done)

    async def handle_client(self, client_reader, client_writer, client_num):
        self.logger.debug("getting remote name...")
        client_name = await asyncio.wait_for(client_reader.readline(), timeout=10.0)
        client_name = client_name.decode().rstrip()

        self.client_writers[client_name] = client_writer
        self.logger.debug("'%s' has connected" % client_name)

        while True:
            if self.timeout is None:
                data = await client_reader.readline()
            else:
                data = await asyncio.wait_for(client_reader.readline(), timeout=self.timeout)

            if data is None or len(data) == 0:
                self.logger.debug("Received no data")
                # exit echo loop and disconnect
                # self.exit()
                return

            sdata = data.decode().rstrip()
            self.received(client_writer, sdata)

            # response = ("ECHO: %s\n" % (sdata))
            # client_writer.write(response.encode())

    def write(self, arg, line):
        line += "\n"
        if type(arg) == str:  # arg is remote name
            self.client_writers[arg].write(line.encode())
        else:  # arg is writer
            arg.write(line.encode())

    def received(self, writer, data):
        pass
