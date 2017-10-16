import os
import time
import logging


def make_logger(name, level, log_format=None, write=True, file_name=None, directory=None, custom_fields_fn=None):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    print_handle = logging.StreamHandler()
    print_handle.setLevel(level)

    if log_format is None:
        log_format = "[%(name)s @ %(filename)s:%(lineno)d][%(levelname)s] %(asctime)s: %(message)s"

    # give the string format to the logger to use for formatting messages
    formatter = logging.Formatter(log_format)
    print_handle.setFormatter(formatter)
    logger.addHandler(print_handle)

    if custom_fields_fn is not None:
        # add custom fields (by default a version field is added)
        stream_filter = logging.Filter()
        stream_filter.filter = custom_fields_fn
        logger.addFilter(stream_filter)

    # initialize a default log file name and directory if none are specified
    if file_name is None:
        file_name = time.strftime("%H;%M;%S.log")
        if directory is None:
            # only use default if both directory and file_name are None.
            # Assume file_name has the full path if directory is None
            directory = time.strftime(os.path.join("logs", "%Y_%b_%d", name))

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

    return logger
