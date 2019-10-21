import os
import logging
import getpass
import asyncio
import aiofiles
import random
import synapseclient as syn
import synapseclient.utils as syn_utils
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
            syn.utils.printTransferProgress = lambda *a, **k: None

            cls._synapse_client = syn.Synapse(skip_checks=True)
            cls._synapse_client.login(username, password, silent=True)
        except Exception as ex:
            cls._synapse_client = None
            logging.error('Synapse login failed: {0}'.format(str(ex)))

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
        @classmethod
        async def rest_post(cls, url, endpoint=None, headers=None, body=None):
            max_attempts = 3
            attempt_number = 0

            while True:
                can_retry = True
                try:
                    uri, headers = SynapseProxy.client()._build_uri_and_headers(url, endpoint=endpoint, headers=headers)

                    if 'signature' in headers and isinstance(headers['signature'], bytes):
                        headers['signature'] = headers['signature'].decode("utf-8")

                    async with AioManager.AIOSESSION.post(uri,
                                                          headers=headers,
                                                          json=body,
                                                          raise_for_status=False) as response:
                        can_retry = (response.status < 400)
                        response.raise_for_status()
                        return await response.json()
                except Exception as ex:
                    logging.exception(ex)
                    attempt_number += 1
                    if attempt_number < max_attempts and can_retry:
                        sleep_time = random.randint(1, 5)
                        logging.info('  Retrying POST in: {0}'.format(sleep_time))
                        await asyncio.sleep(sleep_time)
                    else:
                        logging.error('  Failed POST: {0}'.format(url))
                        raise

        @classmethod
        async def download_file(cls, url, local_path, total_size):
            max_attempts = 3
            attempt_number = 0
            mb_total_size = Utils.pretty_size(total_size)

            while True:
                can_retry = True
                try:
                    async with AioManager.AIOSESSION.get(url, raise_for_status=False) as response:
                        can_retry = (response.status < 400)
                        response.raise_for_status()

                        async with aiofiles.open(local_path, mode='wb') as fd:
                            bytes_read = 0
                            while True:
                                chunk = await response.content.read(Utils.CHUNK_SIZE)
                                if not chunk:
                                    break
                                bytes_read += len(chunk)
                                Utils.print_inplace(
                                    'Saving {0} of {1}'.format(Utils.pretty_size(bytes_read), mb_total_size))

                                await fd.write(chunk)
                            Utils.print_inplace('')
                            logging.info('Saved {0}'.format(Utils.pretty_size(bytes_read)))
                            assert bytes_read == total_size
                            break
                except Exception as ex:
                    logging.exception(ex)
                    attempt_number += 1
                    if attempt_number < max_attempts and can_retry:
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
            request = {
                'parentId': parent if isinstance(parent, str) else parent.id,
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
