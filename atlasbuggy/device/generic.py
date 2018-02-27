import asyncio
from multiprocessing import Event, Queue, Process

from ..node import Node


class Generic(Node):
    def __init__(self, enabled=True, logger=None):
        super(Generic, self).__init__(enabled, logger)

        self.device_port = None
        self.device_start_event = Event()
        self.device_exit_event = Event()
        self.device_read_queue = Queue()
        self.device_write_queue = Queue()
        self.device_process = Process(target=self.manage_device)

    def device_active(self):
        return not self.device_exit_event.is_set()

    def manage_device(self):
        try:
            self.poll_device()
        except BaseException as error:
            self.device_exit_event.set()
            self.logger.debug("Catching exception in device process")
            self.logger.exception(error)
            raise

    def stop_device(self):
        self.device_exit_event.set()

    def poll_device(self):
        """
        example implementation:

        while self.device_active():
            ... poll sensor(s) ...

            self.device_read_queue.put((current_time, data))

            if not self.device_write_queue.empty():
                while not self.device_write_queue.empty():
                    data = self.device_write_queue.get()
                    ... send data ...

        """
        raise NotImplementedError("Please override this method")

    def write(self, packet):
        self.device_write_queue.put(packet)

    def read(self):
        return self.device_read_queue.get()

    def empty(self):
        return self.device_read_queue.empty()

    def start(self):
        if not self.device_start_event.is_set():
            self.device_process.start()
            self.device_start_event.set()
        else:
            self.logger.warning("Device start already called!!")


    @asyncio.coroutine
    def teardown(self):
        self.logger.info("Tearing down device")
        self.device_exit_event.set()
