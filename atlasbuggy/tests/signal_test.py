
import asyncio
import signal

loop = asyncio.get_event_loop()


class Connector:
    def __init__(self):
        self.closing = False
        self.closed = asyncio.Future()
        task = loop.create_task(self.connection_with_client())
        task.add_done_callback(self.closed.set_result)

    async def connection_with_client(self):
        while not self.closing:
            print('Read/write to open connection')
            await asyncio.sleep(0.0)

        print('I will now close connection')
        await asyncio.sleep(0.0)


conn = Connector()


def stop(loop):
    conn.closing = True
    print("from here I will wait until connection_with_client has finished")
    conn.closed.add_done_callback(lambda _: loop.stop())


loop.add_signal_handler(signal.SIGINT, stop, loop)
loop.run_forever()
loop.close()
