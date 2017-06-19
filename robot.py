import os
import time
import logging
import asyncio
import lzma as xz
from atlasbuggy.datastream import DataStream, AsyncStream, ThreadedStream


class Robot:
    def __init__(self, setup_fn=None, loop_fn=None, close_fn=None, event_loop=None, **log_options):
        self.streams = []

        self.loop_fn = loop_fn
        self.setup_fn = setup_fn
        self.stop_fn = close_fn

        self.loop_started = False

        self.log_info = dict(
            file_name=None,
            directory=None,
            write=False,
            log_level=logging.CRITICAL,
            format="[%(name)s @ %(filename)s:%(lineno)d][%(levelname)s] %(asctime)s: %(message)s",
            file_handle=None
        )
        self.log_info.update(log_options)
        self.init_logger()
        self.logger = logging.getLogger(self.__class__.__name__)

        DataStream._log_info = self.log_info

        if event_loop is None:
            self.loop = asyncio.get_event_loop()
        else:
            self.loop = event_loop
        self.coroutine = None

    def init_logger(self):
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

        if self.log_info["write"]:
            self.log_info["file_handle"] = logging.FileHandler(
                os.path.join(self.log_info["directory"], self.log_info["file_name"]), "w+")
            self.log_info["file_handle"].setLevel(logging.DEBUG)
            formatter = logging.Formatter(self.log_info["format"])
            self.log_info["file_handle"].setFormatter(formatter)

    def run(self, *streams):
        for stream in streams:
            if stream.enabled:
                self.streams.append(stream)

        try:
            if len(self.streams) > 0:
                self.coroutine, threads = self.get_loops()

                for stream in self.streams:
                    stream._start()

                if self.setup_fn is not None:
                    self.setup_fn(self)

                self.loop.run_until_complete(self.coroutine)
                self.loop_started = True

                for thread in threads:
                    thread.join()
            else:
                logging.warning("No streams to run!")
        except BaseException:
            self.stop()
            raise
        self.stop()

    def stop(self):
        if self.stop_fn is not None:
            self.stop_fn(self)
        self.exit()

        if self.loop_started:
            if self.coroutine is not None:
                self.coroutine.cancel()
            self.loop.close()

        for stream in self.streams:
            stream.stopped()

        self.logger.debug("applying regex end character\n[")
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
                stream.asyncio_loop = self.loop
                task = stream._run()
                tasks.append(task)
                stream.task = task

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
