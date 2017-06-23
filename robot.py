import os
import time
import logging
import asyncio
import lzma as xz
from atlasbuggy.datastream import DataStream, AsyncStream, ThreadedStream


class Robot:
    version = "1.0"

    def __init__(self, setup_fn=None, loop_fn=None, close_fn=None, event_loop=None, **log_options):
        self.streams = []

        self.loop_fn = loop_fn
        self.setup_fn = setup_fn
        self.stop_fn = close_fn

        self.coroutines_started = False

        if event_loop is None:
            self.loop = asyncio.get_event_loop()
        else:
            self.loop = event_loop
        self.coroutine = None

        self.logger = logging.getLogger(self.__class__.__name__)
        self.log_info = dict(
            file_name=None,
            directory=None,
            write=False,
            log_level=logging.CRITICAL,
            format="[%(name)s, v%(version)s @ %(filename)s:%(lineno)d][%(levelname)s] %(asctime)s: %(message)s",
            file_handle=None
        )
        self.log_info.update(log_options)
        self.init_logger()
        DataStream._log_info = self.log_info

        self.logger.debug(
            "logger initialized: file_name: %(file_name)s, directory: %(directory)s, "
            "write: %(write)s, log_level: %(log_level)s" % self.log_info
        )

    def init_logger(self):
        self.logger.setLevel(logging.DEBUG)

        print_handle = logging.StreamHandler()
        print_handle.setLevel(self.log_info["log_level"])

        formatter = logging.Formatter(self.log_info["format"])
        print_handle.setFormatter(formatter)
        self.logger.addHandler(print_handle)

        stream_filter = logging.Filter()
        stream_filter.filter = self.log_filter

        self.logger.addFilter(stream_filter)

        if self.log_info["file_name"] is None:
            self.log_info["file_name"] = time.strftime("%H;%M;%S.log")
            if self.log_info["directory"] is None:
                # only use default if both directory and file_name are None.
                # Assume file_name has the full path if directory is None
                self.log_info["directory"] = time.strftime("logs/%Y_%b_%d")

        # make directory if writing a log, if directory is not None or empty, and if the directory doesn't exist
        if self.log_info["write"] and self.log_info["directory"] and not os.path.isdir(
                self.log_info["directory"]):
            os.makedirs(self.log_info["directory"])
            self.logger.debug("Creating log directory: %s" % self.log_info["directory"])

        if self.log_info["write"]:
            log_path = os.path.join(self.log_info["directory"], self.log_info["file_name"])
            self.log_info["file_handle"] = logging.FileHandler(log_path, "w+")
            self.log_info["file_handle"].setLevel(logging.DEBUG)
            self.log_info["file_handle"].setFormatter(formatter)
            self.logger.addHandler(self.log_info["file_handle"])

            self.logger.debug("Logging to: %s" % log_path)

    def log_filter(self, record):
        record.version = self.version
        return True

    def run(self, *streams):
        for stream in streams:
            if stream.enabled:
                self.streams.append(stream)

        self.logger.debug("Active streams: %s" % str(self.streams))

        try:
            if len(self.streams) > 0:
                self.coroutine, thread_streams = self.get_loops()

                self.logger.debug("Starting streams, threads have started")
                for stream in self.streams:
                    stream._start()

                self.logger.debug("Calling setup_fn")
                if self.setup_fn is not None:
                    self.setup_fn(self)

                self.logger.debug("Starting coroutine")
                self.loop.run_until_complete(self.coroutine)
                self.coroutines_started = True
                self.logger.debug("Coroutines complete")

                for thread_stream in thread_streams:
                    self.logger.debug("Joining thread stream: %s" % thread_stream)
                    thread_stream.join()

                self.logger.debug("Robot has finished")
            else:
                logging.warning("No streams to run!")
        except BaseException as error:
            self.logger.debug("Catching exception")
            self.logger.exception(error)
            self.stop()
            raise
        self.stop()
        self.logger.debug("applying regex end character:\n[")

    def stop(self):
        self.logger.debug("Calling stop")
        if self.stop_fn is not None:
            self.stop_fn(self)

        self.logger.debug("Exit event set")
        self.exit()

        self.logger.debug("Canceling coroutines")
        if self.coroutines_started:
            if self.coroutine is not None:
                self.coroutine.cancel()
            self.loop.close()
        self.logger.debug("Coroutines canceled")

        self.logger.debug("Calling post stop methods")
        for stream in self.streams:
            stream.stopped()

        self.compress_log()

    def compress_log(self):
        if self.log_info["write"]:
            full_path = os.path.join(self.log_info["directory"], self.log_info["file_name"])
            with open(full_path, "r") as log, open(full_path + ".xz", "wb") as out:
                out.write(xz.compress(log.read().encode()))
            os.remove(full_path)

    def get_loops(self):
        tasks = []
        threads = []
        for stream in self.streams:
            if not isinstance(stream, DataStream):
                raise RuntimeError("Found an object that isn't a stream!", repr(stream))

            if isinstance(stream, AsyncStream):
                task = stream._run()
                tasks.append(task)
                stream.task = task
                stream.asyncio_loop = self.loop

            elif isinstance(stream, ThreadedStream):
                threads.append(stream)

        if self.loop_fn is not None:
            tasks.append(self.loop_fn(self))

        coroutine = asyncio.gather(*tasks)
        for stream in self.streams:
            stream.coroutine = coroutine

        return coroutine, threads

    @staticmethod
    def exit():
        DataStream.exit()
