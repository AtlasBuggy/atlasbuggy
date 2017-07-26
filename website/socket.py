import asyncio
from ..datastream import AsyncStream


class SocketClient(AsyncStream):
    def __init__(self, name, host, port=5001, enabled=True, log_level=None, timeout=5):
        super(SocketClient, self).__init__(enabled, name, log_level)
        self.host = host
        self.port = port
        self.timeout = timeout

        self.reader = None
        self.writer = None

    async def run(self):
        self.logger.debug("Awaiting connection")
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port, loop=self.asyncio_loop)
        self.logger.debug("Connection opened with %s:%s" % (self.host, self.port))

        self.write(self.name + "\n")
        while self.is_running():
            await self.update()

        self.logger.debug("Disconnected from %s %d" % (self.host, self.port))

    async def read(self, n=-1):
        if self.timeout is not None:
            data = await asyncio.wait_for(self.reader.read(n), timeout=self.timeout)
        else:
            data = await self.reader.read(n)

        if data is None or len(data) == 0:
            self.logger.warning("socket received nothing")
            self.exit()
        return data

    async def update(self):
        await self.read()

    def write(self, data):
        if self.writer is None:
            raise Exception("async socket not started!")
        data += "\n"
        self.writer.write(data.encode())

    def stop(self):
        self.writer.write_eof()
        self.exit()


class SocketServer(AsyncStream):
    def __init__(self, enabled=True, log_level=None, name=None, host='0.0.0.0', port=5001, timeout=1):
        super(SocketServer, self).__init__(enabled, name, log_level)

        self.host = host
        self.port = port
        self.timeout = timeout

        self.client_writers = {}

    async def run(self):
        self.logger.debug("Starting server on %s:%s" % (self.host, self.port))
        await asyncio.start_server(self.accept_client, host=self.host, port=self.port)
        while self.is_running():
            await self.update()
        self.logger.debug("socket server exiting")

    def accept_client(self, client_reader, client_writer):
        self.logger.debug("Receiving client: %s, %s" % (client_reader, client_writer))
        task = asyncio.Task(self.handle_client(client_reader, client_writer))

        def client_done(end_task):
            closed_client_name = end_task.result()
            del self.client_writers[closed_client_name]
            client_writer.close()
            self.logger.debug("ending connection")

            self.client_connected(closed_client_name)

        task.add_done_callback(client_done)

    async def handle_client(self, client_reader, client_writer):
        self.logger.debug("getting remote name...")
        client_name = await asyncio.wait_for(client_reader.readline(), timeout=10.0)
        client_name = client_name.decode().rstrip()
        if client_name in self.client_writers:
            self.logger.error("Client named %s already connected! Ignoring." % client_name)
            return client_name

        self.client_writers[client_name] = client_writer
        self.logger.debug("'%s' has connected" % client_name)

        self.client_connected(client_name)

        try:
            while self.is_running():
                if self.timeout is None:
                    data = await client_reader.readline()
                else:
                    data = await asyncio.wait_for(client_reader.readline(), timeout=self.timeout)

                if data is None or len(data) == 0:
                    self.logger.debug("Received no data")
                    return client_name

                sdata = data.decode().rstrip()
                self.received(client_writer, client_name, sdata)
        except ConnectionResetError as error:
            self.logger.exception(error)
            return client_name

    def client_connected(self, name):
        pass

    def client_disconnected(self):
        pass

    def write(self, client, line, append_newline=True):
        if type(line) == str:
            if append_newline:
                line += "\n"
            line = line.encode()
        elif type(line) == bytes:
            if append_newline:
                line += b'\n'
        else:
            raise ValueError("line must be bytes or str: %s" % line)

        if type(client) == str:  # arg is remote name, otherwise arg is writer
            client = self.client_writers[client]

        client.write(line)

    def write_all(self, line, append_newline=True):
        for client in self.client_writers.values():
            self.write(client, line, append_newline)

    def received(self, writer, name, data):
        pass

    async def update(self):
        await asyncio.sleep(0.5)
