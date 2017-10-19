import os
import time
import logging
from logging import handlers
import queue


def make_logger(name, default_settings, level=None,
                write=None, log_format=None, file_name=None, directory=None, custom_fields_fn=None):
    # log_queue = queue.Queue(-1)  # no limit on size
    # queue_handler = handlers.QueueHandler(log_queue)

    if level is None:
        level = default_settings["level"]

    print_handle = logging.StreamHandler()
    print_handle.setLevel(level)

    # listener = handlers.QueueListener(log_queue, print_handle)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # logger.addHandler(queue_handler)

    if log_format is None:
        log_format = default_settings["log_format"]

    if write is None:
        write = default_settings["write"]

    # give the string format to the logger to use for formatting messages
    formatter = logging.Formatter(log_format)
    print_handle.setFormatter(formatter)
    logger.addHandler(print_handle)

    if custom_fields_fn is None:
        custom_fields_fn = default_settings["custom_fields_fn"]

    if custom_fields_fn is not None:
        # add custom fields (by default a version field is added)
        stream_filter = logging.Filter()
        stream_filter.filter = custom_fields_fn
        logger.addFilter(stream_filter)

    # initialize a default log file name and directory if none are specified
    if file_name is None:
        if "%" in default_settings["file_name"]:
            file_name = time.strftime(default_settings["file_name"])
        else:
            file_name = default_settings["file_name"]

        if directory is None:
            # only use default if both directory and file_name are None.
            # Assume file_name has the full path if directory is None
            directory_format = default_settings["directory"]
            directory_parts = []

            directory_format = os.path.normpath(directory_format)
            for part in directory_format.split(os.sep):
                if "%(name)s" in part:
                    directory_parts.append(part % dict(name=name))

                elif "%" in directory_format:
                    directory_parts.append(time.strftime(part))

            directory = os.path.join(*directory_parts)

    # make directory if writing a log, if directory evaluates True, and if the directory doesn't exist
    if write and directory and not os.path.isdir(directory):
        os.makedirs(directory)
        logger.debug("Creating log directory: %s" % directory)

    # if writing a log, initialize the logging file handle
    if write:
        log_path = os.path.join(directory, file_name)
        file_handle = logging.FileHandler(log_path, "w+")
        file_handle.setLevel(logging.DEBUG)
        file_handle.setFormatter(formatter)
        logger.addHandler(file_handle)

        logger.debug("Logging to: %s" % log_path)


    # listener.start()
    return logger
