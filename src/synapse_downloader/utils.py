import os
import sys
import logging
import asyncio
import random
import hashlib
import aiofiles


class Utils:
    MB = 2 ** 20
    CHUNK_SIZE = 10 * MB

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

    @staticmethod
    async def rest_post(aiosession, url, headers=None, body=None):
        max_attempts = 5
        attempt_number = 0
        while True:
            try:
                async with aiosession.post(url, headers=headers, json=body) as response:
                    return await response.json()
            except Exception as ex:
                logging.exception(ex)
                attempt_number += 1
                if attempt_number < max_attempts:
                    sleep_time = random.randint(1, 5)
                    logging.info('  Retrying POST in: {0}'.format(sleep_time))
                    await asyncio.sleep(sleep_time)
                else:
                    logging.error('  Failed POST: {0}'.format(url))
                    raise

    @staticmethod
    async def download_file(aiosession, url, local_path, total_size):
        max_attempts = 5
        attempt_number = 0
        while True:
            try:
                async with aiosession.get(url) as response:
                    async with aiofiles.open(local_path, mode='wb') as fd:
                        chunk_size_read = 0
                        while True:
                            chunk = await response.content.read(Utils.CHUNK_SIZE)
                            if not chunk:
                                break
                            chunk_size_read += len(chunk)
                            sys.stdout.write('\r')
                            sys.stdout.flush()
                            sys.stdout.write('  Saving chunk {0} of {1}'.format(chunk_size_read, total_size))
                            sys.stdout.flush()
                            await fd.write(chunk)
                        print('')
                        logging.info('  Saved {0} bytes'.format(chunk_size_read))
                        break
            except Exception as ex:
                logging.exception(ex)
                attempt_number += 1
                if attempt_number < max_attempts:
                    sleep_time = random.randint(1, 5)
                    logging.error('  Retrying file in: {0}'.format(sleep_time))
                    await asyncio.sleep(sleep_time)
                else:
                    logging.error('  Failed to download file: {0}'.format(local_path))
                    raise

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
