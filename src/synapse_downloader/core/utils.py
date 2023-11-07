import os
import re
import math
import pathlib
import logging
from .env import Env


class Utils:
    KB = 1024
    MB = KB * KB
    CHUNK_SIZE = 10 * MB

    @staticmethod
    def os_name():
        return os.name

    @staticmethod
    def patch():
        """Applies patches to packages"""
        if Env.SYNTOOLS_PATCH() is True:
            # On windows this method will lowercase all directory and file names.
            # We do not want this since it changes the data and breaks uploading and comparisons.
            if Utils.os_name() == 'nt':
                from synapseclient.core import utils
                logging.info('Patching synapseclient.', console=True)

                def normalize_path(path):
                    """Transforms a path into an absolute path with forward slashes only."""
                    if path is None:
                        return None
                    return re.sub(r'\\', '/', os.path.abspath(path))

                utils.normalize_path = normalize_path

    @staticmethod
    def real_path(path):
        return str(pathlib.Path(path).resolve())

    @staticmethod
    def app_dir():
        """Gets the application's primary directory for the current user.

        Returns:
            Absolute path to the directory.
        """
        return os.path.join(pathlib.Path.home(), '.syntools')

    @staticmethod
    def app_log_dir():
        """Gets the applications primary log directory for the current user.

        Returns:
            Absolute path to the directory.
        """
        return os.path.join(Utils.app_dir(), 'logs')

    @staticmethod
    def expand_path(local_path):
        var_path = os.path.expandvars(local_path)
        expanded_path = os.path.expanduser(var_path)
        return os.path.abspath(expanded_path)

    @staticmethod
    def ensure_dirs(local_path):
        """Ensures the directories in local_path exist.

        Args:
            local_path: The local path to ensure.

        Returns:
            None
        """
        if not os.path.isdir(local_path):
            os.makedirs(local_path)

    # Hold the names for pretty printing file sizes.
    PRETTY_SIZE_NAMES = ("Bytes", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")

    @staticmethod
    def pretty_size(size):
        if size is None:
            return 'Unknown'
        elif size > 0:
            i = int(math.floor(math.log(size, 1024)))
            p = math.pow(1024, i)
            s = round(size / p, 2)
        else:
            i = 0
            s = 0
        return '{0} {1}'.format(s, Utils.PRETTY_SIZE_NAMES[i])

    # Holds the last string that was printed
    __last_print_inplace_len = 0

    @staticmethod
    def print_inplace(msg):
        # Clear the line. Using this method so it works on Windows too.
        print(' ' * Utils.__last_print_inplace_len, end='\r')
        print(msg, end='\r')
        Utils.__last_print_inplace_len = len(msg)
