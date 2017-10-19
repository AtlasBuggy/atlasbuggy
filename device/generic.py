import asyncio
from multiprocessing import Event, Queue, Process

from atlasbuggy.node import Node


class Generic(Node):
    def __init__(self, enabled=True, logger=None):
        super(Generic, self).__init__(enabled, logger)

        self.device = None
        self.device_exit_event = Event()
        self.device_read_queue = Queue()
        self.device_write_queue = Queue()
        self.device_process = Process(target=self.manage_device)

    def configure_device(self):
        pass

    def device_active(self):
        return not self.device_exit_event.is_set()

    def manage_device(self):
        try:
            self.configure_device()
            self.poll_device()
        except BaseException:
            self.device_exit_event.set()
            raise

    def stop_device(self):
        self.device_exit_event.set()

    def poll_device(self):
        pass

    async def setup(self):
        self.device_process.start()

    async def teardown(self):
        self.logger.info("Tearing down device")
        self.device_exit_event.set()
