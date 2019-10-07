import os


class Utils:
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
