import os
import logging
import getpass
import asyncio
import aiohttp
import aiofiles
import random
import hashlib
import synapseclient as syn
from functools import partial
from .utils import Utils
from .aio_manager import AioManager


class SynapseProxy:
    _synapse_client = None

    @classmethod
    def login(cls, username=None, password=None):
        username = username or os.getenv('SYNAPSE_USERNAME')
        password = password or os.getenv('SYNAPSE_PASSWORD')

        if not username:
            username = input('Synapse username: ')

        if not password:
            password = getpass.getpass(prompt='Synapse password: ')

        logging.info('Logging into Synapse as: {0}'.format(username))
        try:
            # Disable the synapseclient progress output.
            syn.core.utils.printTransferProgress = lambda *a, **k: None

            cls._synapse_client = syn.Synapse(skip_checks=True)
            cls._synapse_client.login(username, password, silent=True)
        except Exception as ex:
            cls._synapse_client = None
            logging.error('Synapse login failed: {0}'.format(str(ex)))

        return cls._synapse_client is not None

    @classmethod
    def logged_in(cls):
        return cls._synapse_client is not None

    @classmethod
    def client(cls):
        if not cls._synapse_client:
            cls.login()
        return cls._synapse_client

    @classmethod
    def store(cls, obj, **kwargs):
        return cls.client().store(obj, **kwargs)

    @classmethod
    async def storeAsync(cls, obj, **kwargs):
        args = partial(cls.store, obj=obj, **kwargs)
        return await asyncio.get_running_loop().run_in_executor(None, args)

    @classmethod
    def get(cls, entity, **kwargs):
        return cls.client().get(entity, **kwargs)

    @classmethod
    async def getAsync(cls, entity, **kwargs):
        args = partial(cls.get, entity=entity, **kwargs)
        return await asyncio.get_running_loop().run_in_executor(None, args)

    @classmethod
    def getChildren(cls, parent, **kwargs):
        return list(cls.client().getChildren(parent, **kwargs))

    @classmethod
    async def getChildrenAsync(cls, parent, **kwargs):
        args = partial(cls.getChildren, parent=parent, **kwargs)
        return await asyncio.get_running_loop().run_in_executor(None, args)

    @classmethod
    def tableQuery(cls, query, resultsAs="csv", **kwargs):
        return cls.client().tableQuery(query=query, resultsAs=resultsAs, **kwargs)

    @classmethod
    async def tableQueryAsync(cls, query, resultsAs="csv", **kwargs):
        args = partial(cls.tableQuery, query=query, resultsAs=resultsAs, **kwargs)
        return await asyncio.get_running_loop().run_in_executor(None, args)

    @classmethod
    def delete(cls, obj, version=None):
        return cls.client().delete(obj, version=version)

    @classmethod
    async def deleteAsync(cls, obj, version=None):
        args = partial(cls.delete, obj=obj, version=version)
        return await asyncio.get_running_loop().run_in_executor(None, args)

    class Aio:
        # File downloads have a max of 1 hour to download.
        FILE_DOWNLOAD_TIMEOUT = 60 * 60

        @classmethod
        def _get_syn_http_headers(cls, url, endpoint=None, headers=None):
            if headers is None:
                headers = {}

            uri, syn_headers = SynapseProxy.client()._build_uri_and_headers(url, endpoint=endpoint, headers=headers)

            headers.update(syn_headers)

            # This is needed for newer versions of the synapseclient.
            # Older versions will have the signature from _build_uri_and_headers.
            if not 'signature' in headers:
                signed_headers = SynapseProxy.client().credentials.get_signed_headers(uri)
                headers.update(signed_headers)

            if 'signature' in headers and isinstance(headers['signature'], bytes):
                headers['signature'] = headers['signature'].decode("utf-8")

            return uri, headers

        @classmethod
        async def rest_post(cls, url, endpoint=None, headers=None, body=None):
            max_attempts = 3
            attempt_number = 0

            while True:
                try:
                    uri, headers = cls._get_syn_http_headers(url, endpoint=endpoint, headers=headers)
                    async with AioManager.AIOSESSION.post(uri, headers=headers, json=body) as response:
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

        @classmethod
        async def download_file(cls, syn_id, local_path, filehandle, filehandle_func):
            # TODO: Add resume ability for downloads.
            max_attempts = 3
            attempt_number = 0

            while True:
                try:
                    if attempt_number > 0:
                        # Get a new filehandle for retries so the preSignedURL is fresh.
                        filehandle = await filehandle_func(syn_id)

                    url = filehandle.get('preSignedURL')
                    remote_md5 = filehandle.get('fileHandle').get('contentMd5')
                    total_size = filehandle.get('fileHandle').get('contentSize')
                    # NOTE: For ExternalFileHandles the size and MD5 data will not be present.
                    is_unknown_size = total_size is None

                    pretty_size = Utils.pretty_size(total_size)
                    timeout = aiohttp.ClientTimeout(total=cls.FILE_DOWNLOAD_TIMEOUT)

                    async with AioManager.AIOSESSION.get(url, timeout=timeout) as response:
                        async with aiofiles.open(local_path, mode='wb') as fd:
                            bytes_read = 0
                            download_md5 = hashlib.md5()
                            while True:
                                chunk = await response.content.read(Utils.CHUNK_SIZE)
                                if not chunk:
                                    break
                                bytes_read += len(chunk)
                                Utils.print_inplace(
                                    'Saving {0} of {1}'.format(Utils.pretty_size(bytes_read), pretty_size))

                                await fd.write(chunk)
                                download_md5.update(chunk)

                            Utils.print_inplace('')
                            logging.info('Saved {0}'.format(Utils.pretty_size(bytes_read)))

                            if not is_unknown_size:
                                if bytes_read != total_size:
                                    raise Exception(
                                        'Bytes downloaded: {0} does not match remote size: {1}'.format(bytes_read,
                                                                                                       total_size))

                                local_md5 = download_md5.hexdigest()
                                if local_md5 != remote_md5:
                                    raise Exception(
                                        'Local MD5: {0} does not match remote MD5: {1}'.format(local_md5, remote_md5))
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

        @classmethod
        async def get_children(cls,
                               parent,
                               includeTypes=["folder", "file", "table", "link", "entityview", "dockerrepo"],
                               sortBy="NAME",
                               sortDirection="ASC"):
            parent_id = parent
            if isinstance(parent, str):
                parent_id = parent
            elif isinstance(parent, syn.Entity):
                parent_id = parent.id
            elif isinstance(parent, dict):
                parent_id = parent['id']
            else:
                raise Exception('Invalid parent object: {0}'.format(parent))

            request = {
                'parentId': parent_id,
                'includeTypes': includeTypes,
                'sortBy': sortBy,
                'sortDirection': sortDirection,
                'includeTotalChildCount': True,
                'nextPageToken': None
            }

            response = {"nextPageToken": "first"}
            while response.get('nextPageToken') is not None:
                response = await cls.rest_post('/entity/children', body=request)
                for child in response['page']:
                    yield child
                request['nextPageToken'] = response.get('nextPageToken', None)

        @classmethod
        async def get_file_handle_id(cls, syn_id):
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

            res = await cls.rest_post('/entity/{0}/bundle2'.format(syn_id), body=request)

            return res.get('entity').get('dataFileHandleId')

        @classmethod
        async def get_filehandle(cls, syn_id, file_handle_id):
            body = {
                'includeFileHandles': True,
                'includePreSignedURLs': True,
                'includePreviewPreSignedURLs': False,
                'requestedFiles': [{
                    'fileHandleId': file_handle_id,
                    'associateObjectId': syn_id,
                    'associateObjectType': 'FileEntity'
                }]
            }

            res = await cls.rest_post('/fileHandle/batch',
                                      endpoint=SynapseProxy.client().fileHandleEndpoint,
                                      body=body)

            return res.get('requestedFiles', [])[0]
