import os
import hashlib
import aiofiles
import math
import pathlib


class Utils:
    KB = 1024
    MB = KB * KB
    CHUNK_SIZE = 10 * MB

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

    @staticmethod
    def split_chunk(list, chunk_size):
        """Yield successive n-sized chunks from a list.

        Args:
            list: The list to chunk.
            chunk_size: The max chunk size.

        Returns:
            List of lists.
        """
        for i in range(0, len(list), chunk_size):
            yield list[i:i + chunk_size]

    # Holds the last string that was printed
    __last_print_inplace_len = 0

    @staticmethod
    def print_inplace(msg):
        # Clear the line. Using this method so it works on Windows too.
        print(' ' * Utils.__last_print_inplace_len, end='\r')
        print(msg, end='\r')
        Utils.__last_print_inplace_len = len(msg)

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

    @staticmethod
    async def get_md5(local_path):
        md5 = hashlib.md5()
        async with aiofiles.open(local_path, mode='rb') as fd:
            while True:
                chunk = await fd.read(Utils.CHUNK_SIZE)
                if not chunk:
                    break
                md5.update(chunk)
        return md5.hexdigest()
