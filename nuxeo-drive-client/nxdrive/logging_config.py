"""Utilities to log nxdrive operations and failures"""

import logging
from logging.handlers import RotatingFileHandler
import os


TRACE = 5
logging.addLevelName(TRACE, 'TRACE')
logging.TRACE = TRACE
FILE_HANDLER = None

# Singleton logging context for each process.
# Alternatively we could use the setproctitle to handle the command name
# package and directly change the real process name but this requires to build
# a compiled extension under Windows...

_logging_context = dict()

is_logging_configured = False


def configure(use_file_handler=False, log_filename=None, file_level='INFO',
              console_level='INFO', filter_inotify=True, command_name=None, log_rotate_keep=3,
              log_rotate_max_bytes=100000000, force_configure=False):

    global is_logging_configured
    global FILE_HANDLER

    if not is_logging_configured or force_configure:
        is_logging_configured = True

        _logging_context['command'] = command_name

        if file_level is None:
            file_level = 'INFO'
        # convert string levels
        if hasattr(file_level, 'upper'):
            file_level = getattr(logging, file_level.upper())
        if hasattr(console_level, 'upper'):
            console_level = getattr(logging, console_level.upper())

        # find the minimum level to avoid filtering by the root logger itself:
        root_logger = logging.getLogger()
        min_level = min(file_level, console_level)
        root_logger.setLevel(min_level)

        # define the formatter
        formatter = logging.Formatter(
            "%(asctime)s %(process)d %(thread)d %(levelname)-8s %(name)-18s"
            " %(message)s"
        )

        # define a Handler which writes INFO messages or higher to the
        # sys.stderr
        console_handler_name = 'console'
        console_handler = get_handler(root_logger, console_handler_name)
        if console_handler is None:
            console_handler = logging.StreamHandler()
            console_handler.set_name(console_handler_name)
            # tell the console handler to use this format
            console_handler.setFormatter(formatter)
        console_handler.setLevel(console_level)

        # add the console handler to the root logger and all descendants
        root_logger.addHandler(console_handler)

        # define a Handler for file based log with rotation if needed
        if use_file_handler and log_filename is not None:
            log_filename = os.path.expanduser(log_filename)
            log_folder = os.path.dirname(log_filename)
            if not os.path.exists(log_folder):
                os.makedirs(log_folder)

            file_handler = RotatingFileHandler(
                log_filename, mode='a', maxBytes=log_rotate_max_bytes,
                backupCount=log_rotate_keep)
            file_handler.set_name('file')
            file_handler.setLevel(file_level)
            file_handler.setFormatter(formatter)
            FILE_HANDLER = file_handler
            root_logger.addHandler(file_handler)

        if filter_inotify:
            root_logger.addFilter(logging.Filter('watchdog.observers.inotify_buffer'))


def get_handler(logger, name):
    for handler in logger.handlers:
        if name == handler.get_name():
            return handler
    return None


def get_logger(name):
    logger = logging.getLogger(name)
    trace = lambda *args, **kwargs: logger.log(TRACE, *args, **kwargs)
    setattr(logger, 'trace', trace)
    return logger
