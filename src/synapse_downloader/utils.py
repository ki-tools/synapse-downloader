import os
import sys
import logging
import asyncio
import random
import hashlib
import aiofiles
import synapseclient.utils as syn_utils
from .synapse_proxy import SynapseProxy


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
    def print_inplace(msg):
        sys.stdout.write('\r')
        sys.stdout.flush()
        sys.stdout.write(msg)
        sys.stdout.flush()

    @staticmethod
    async def rest_post(aiosession, url, endpoint=None, headers=None, body=None):
        max_attempts = 3
        attempt_number = 0
        while True:
            try:
                uri, headers = SynapseProxy.client()._build_uri_and_headers(url, endpoint=endpoint, headers=headers)

                if 'signature' in headers and isinstance(headers['signature'], bytes):
                    headers['signature'] = headers['signature'].decode("utf-8")

                async with aiosession.post(uri, headers=headers, json=body) as response:
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
        max_attempts = 3
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
                            Utils.print_inplace('  Saving chunk {0} of {1}'.format(chunk_size_read, total_size))
                            await fd.write(chunk)
                        print('')
                        logging.info('  Saved {0} bytes'.format(chunk_size_read))
                        assert chunk_size_read == total_size
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
    async def get_children(aiosession,
                           parent,
                           includeTypes=["folder", "file", "table", "link", "entityview", "dockerrepo"],
                           sortBy="NAME",
                           sortDirection="ASC"):

        parentId = syn_utils.id_of(parent) if parent is not None else None

        request = {
            'parentId': parentId,
            'includeTypes': includeTypes,
            'sortBy': sortBy,
            'sortDirection': sortDirection,
            'includeTotalChildCount': True,
            'nextPageToken': None
        }

        results = []

        Utils.print_inplace('Fetching children...')

        total_fetched = 0

        response = {"nextPageToken": "first"}
        while response.get('nextPageToken') is not None:
            response = await Utils.rest_post(aiosession, '/entity/children', body=request)

            total_children = response['totalChildCount']
            total_this_req = len(response['page'])
            total_fetched += total_this_req

            Utils.print_inplace('Fetching children: {0} of {1}'.format(total_fetched, total_children))

            for child in response['page']:
                results.append(child)
            request['nextPageToken'] = response.get('nextPageToken', None)
        print('')

        return results

    @staticmethod
    async def get_file_handle_id(aiosession, syn_id):
        request = {
            'includeEntity': True,
            'includeAnnotations': False,
            'includePermissions': False,
            'includeEntityPath': False,
            'includeHasChildren': False,
            'includeAccessControlList': False,
            'includeFileHandles': False,
            'includeTableBundle': False,
            'includeRootWikiId': False,
            'includeBenefactorACL': False,
            'includeDOIAssociation': False,
            'includeFileName': False,
            'includeThreadCount': False,
            'includeRestrictionInformation': False
        }

        res = await Utils.rest_post(aiosession, '/entity/{0}/bundle2'.format(syn_id), body=request)

        return res.get('entity').get('dataFileHandleId')

    @staticmethod
    async def get_filehandle(aiosession, syn_id):
        body = {
            'includeFileHandles': True,
            'includePreSignedURLs': True,
            'includePreviewPreSignedURLs': False,
            'requestedFiles': [{
                'fileHandleId': await Utils.get_file_handle_id(aiosession, syn_id),
                'associateObjectId': syn_id,
                'associateObjectType': 'FileEntity'
            }]
        }

        res = await Utils.rest_post(aiosession,
                                    '/fileHandle/batch',
                                    endpoint=SynapseProxy.client().fileHandleEndpoint,
                                    body=body)
        
        return res.get('requestedFiles', [])[0]

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
