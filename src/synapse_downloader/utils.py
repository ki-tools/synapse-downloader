class Utils:
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
