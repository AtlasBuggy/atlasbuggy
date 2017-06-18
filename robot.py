import os
import time
import logging
import asyncio
import lzma as xz
from atlasbuggy.datastream import DataStream, AsyncStream


class Robot:
    def __init__(self, wait_for_all=True, setup_fn=None, loop_fn=None, close_fn=None, **log_options):
        self.streams = []

        self.wait_for_all = wait_for_all

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

        DataStream._log_info = self.log_info

        self.loop = asyncio.get_event_loop()
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
                self.coroutine = self.get_coroutine()

                for stream in self.streams:
                    stream._start()

                if self.setup_fn is not None:
                    self.setup_fn(self)

                self.loop.run_until_complete(self.coroutine)
                self.loop_started = True

                if self.wait_for_all:
                    while DataStream.all_running():
                        time.sleep(0.1)
                else:

                    while not DataStream.any_stopped():
                        time.sleep(0.1)
            else:
                logging.warning("No streams to run!")
        except BaseException:
            self.stop()
            raise
        self.stop()

    def stop(self):
        if self.stop_fn is not None:
            self.stop_fn(self)
        self.exit_all()
        for stream in self.streams:
            stream._stop()

        if self.loop_started:
            if self.coroutine is not None:
                self.coroutine.cancel()
            self.loop.close()

        self.compress_log()

    def compress_log(self):
        if self.log_info["write"]:
            full_path = os.path.join(self.log_info["directory"], self.log_info["file_name"])
            with open(full_path, "r") as log, open(full_path + ".xz", "wb") as out:
                out.write(xz.compress(log.read().encode()))
            os.remove(full_path)

    def get_coroutine(self):
        tasks = []
        for stream in self.streams:
            if not isinstance(stream, DataStream):
                raise RuntimeError("Found an object that isn't a stream!", repr(stream))
            if isinstance(stream, AsyncStream):
                stream.asyncio_loop = self.loop
                task = stream._run()
                tasks.append(task)
                stream.task = task

        if self.loop_fn is not None:
            tasks.append(self.loop_fn(self))

        coroutine = asyncio.gather(*tasks)
        for stream in self.streams:
            stream.coroutine = coroutine

        return coroutine

    @staticmethod
    def exit_all():
        DataStream.exit_all()
