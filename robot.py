import os
import time
import logging
import asyncio
import lzma as xz
from .datastream import DataStream, AsyncStream, ThreadedStream


class Robot:
    """
    Manages all streams associated with the robot, log initialization, and exception handling
    """

    def __init__(self, setup_fn=None, loop_fn=None, stop_fn=None, event_loop=None, **log_options):
        """
        :param setup_fn: An external function to call at start up if setting up a new stream is too much functionality
        :param loop_fn: An external function to call after all streams have started.
            Put a while loop in this function. Make sure it abides asyncio protocol
        :param stop_fn: An external function to call after all streams have stopped
        :param event_loop: If you have an external asyncio event loop, supply it here 
        :param log_options: current log options: file_name, directory, write, log_level
            log_level: which types of log messages should be displayed? See python's logging module for details
        """
        self.streams = []

        self.loop_fn = loop_fn
        self.setup_fn = setup_fn
        self.stop_fn = stop_fn

        self.coroutines_started = False  # prevents unnecessary coroutine cancellation

        # check if user supplied an event loop
        if event_loop is None:
            self.loop = asyncio.get_event_loop()
        else:
            self.loop = event_loop
        self.coroutine = None

        # initialize the shared logger with this class' name
        self.logger = logging.getLogger(self.__class__.__name__)
        self.log_info = dict(
            file_name=None,
            directory=None,
            write=True,
            log_level=logging.CRITICAL,
            format="[%(name)s @ %(filename)s:%(lineno)d][%(levelname)s] %(asctime)s: %(message)s",
            file_handle=None
        )

        # initialize logger with options
        self.log_info.update(log_options)
        self.init_logger()
        DataStream._log_info = self.log_info

        self.logger.debug(
            "logger initialized: file_name: %(file_name)s, directory: %(directory)s, "
            "write: %(write)s, log_level: %(log_level)s" % self.log_info
        )

    def init_logger(self):
        # accept all log messages. This ensures all log messages are recorded
        self.logger.setLevel(logging.DEBUG)

        # initialize the log printer. Use the supplied log level to determine which messages to print
        print_handle = logging.StreamHandler()
        print_handle.setLevel(self.log_info["log_level"])

        # give the string format to the logger to use for formatting messages
        formatter = logging.Formatter(self.log_info["format"])
        print_handle.setFormatter(formatter)
        self.logger.addHandler(print_handle)

        # add custom fields (by default a version field is added)
        stream_filter = logging.Filter()
        stream_filter.filter = self.log_filter
        self.logger.addFilter(stream_filter)

        # initialize a default log file name and directory if none are specified
        if self.log_info["file_name"] is None:
            self.log_info["file_name"] = time.strftime("%H;%M;%S.log")
            if self.log_info["directory"] is None:
                # only use default if both directory and file_name are None.
                # Assume file_name has the full path if directory is None
                self.log_info["directory"] = time.strftime("logs/%Y_%b_%d")

        # make directory if writing a log, if directory evaluates True, and if the directory doesn't exist
        if self.log_info["write"] and self.log_info["directory"] and not os.path.isdir(
                self.log_info["directory"]):
            os.makedirs(self.log_info["directory"])
            self.logger.debug("Creating log directory: %s" % self.log_info["directory"])

        # if writing a log, initialize the logging file handle
        if self.log_info["write"]:
            log_path = os.path.join(self.log_info["directory"], self.log_info["file_name"])
            self.log_info["file_handle"] = logging.FileHandler(log_path, "w+")
            self.log_info["file_handle"].setLevel(logging.DEBUG)
            self.log_info["file_handle"].setFormatter(formatter)
            self.logger.addHandler(self.log_info["file_handle"])

            self.logger.debug("Logging to: %s" % log_path)

    def log_filter(self, record):
        return True

    def run(self, *streams):
        """
        After all streams are initialized, call robot.run and pass in the initialized streams 
        :param streams: streams for this robot to run
        """

        # ignore stream if it's not enabled
        for stream in streams:
            if stream.enabled:
                self.streams.append(stream)

        self.logger.debug("Active streams: %s" % str(self.streams))

        try:
            if len(self.streams) > 0:
                # get the objects representing the coroutines to run
                self.coroutine, thread_streams = self.get_loops()

                # start all streams. Threaded streams call their _run methods here
                self.logger.debug("Starting streams, threads have started")
                for stream in self.streams:
                    stream._start()

                # call external setup function
                self.logger.debug("Calling setup_fn")
                if self.setup_fn is not None:
                    self.setup_fn(self)

                # start asynchronous coroutines
                self.logger.debug("Starting coroutine")
                self.loop.run_until_complete(self.coroutine)
                self.coroutines_started = True
                self.logger.debug("Coroutines complete")

                # if all coroutines finish, wait for threads to finish if they are still running
                for thread_stream in thread_streams:
                    if not thread_stream.has_stopped() and DataStream.is_running():
                        self.logger.debug(
                            "Joining threaded stream: %s. Thread has stopped: %s. Event event thrown: %s" % (
                                thread_stream, thread_stream.has_stopped(), not DataStream.is_running())
                        )
                        thread_stream.join()
                    else:
                        self.logger.debug("Threaded stream '%s' is already stopped" % thread_stream)

                self.logger.debug("Robot has finished")
            else:
                logging.warning("No streams to run!")
        except BaseException as error:
            self.logger.debug("Catching exception")
            self.logger.exception(error)
            self.stop()
            raise
        self.stop()
        self.logger.debug("finished")

    def stop(self):
        """
        Teardown behavior for the robot. Stops all streams from running
        """
        self.logger.debug("Calling stop")
        if self.stop_fn is not None:
            self.stop_fn(self)

        # signal for streams to exit. They call their own stop methods
        self.logger.debug("Exit event set")
        self.exit()

        # in cause coroutines are still running, call cancel
        self.logger.debug("Canceling coroutines")
        if self.coroutines_started:
            if self.coroutine is not None:
                self.coroutine.cancel()
            self.loop.close()
        self.logger.debug("Coroutines canceled")

        # call each streams' stopped method for post teardown behavior
        self.logger.debug("Calling post stop methods")
        for stream in self.streams:
            stream.stopped()

        # make the log file smaller
        self.compress_log()

    def compress_log(self):
        # if writing a log, use lzma compression on the new log file
        if self.log_info["write"]:
            full_path = os.path.join(self.log_info["directory"], self.log_info["file_name"])
            with open(full_path, "r") as log, open(full_path + ".xz", "wb") as out:
                out.write(xz.compress(log.read().encode()))
            os.remove(full_path)

    def get_loops(self):
        tasks = []
        threads = []
        async_streams = []
        static_streams = []
        # separate async and threaded streams
        for stream in self.streams:
            if not isinstance(stream, DataStream):
                raise RuntimeError("Found an object that isn't a stream!", repr(stream))

            # initialize asynchronous task. Make the loop and task available to all streams (just in case)
            if isinstance(stream, AsyncStream):
                task = stream._run()
                tasks.append(task)
                async_streams.append(stream)
                stream.task = task

            # add thread to the list
            elif isinstance(stream, ThreadedStream):
                threads.append(stream)
            else:
                static_streams.append(stream)

            stream.asyncio_loop = self.loop

        # add loop function as an asynchronous task
        if self.loop_fn is not None:
            tasks.append(self.loop_fn(self))

        # create coroutine. Make it available to all streams (just in case)
        coroutine = asyncio.gather(*tasks)
        for stream in self.streams:
            stream.coroutine = coroutine

        self.logger.debug("Asynchronous streams: %s" % str(async_streams))
        self.logger.debug("Threaded streams: %s" % str(threads))
        self.logger.debug("Static streams: %s" % str(static_streams))

        return coroutine, threads

    @staticmethod
    def exit():
        # signal all streams to exit
        DataStream.exit()

