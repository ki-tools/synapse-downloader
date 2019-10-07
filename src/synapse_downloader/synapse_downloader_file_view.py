import os
import sys
import getpass
import synapseclient as syn
import asyncio
from functools import partial
import logging
import aiohttp
import aiofiles
from datetime import datetime, time
import hashlib
from .syn_parent_iter import SynapseParentIter
from .download_file_view import DownloadFileView
from .utils import Utils
import random


class SynapseDownloaderFileView:
    MB = 2 ** 20
    CHUNK_SIZE = 10 * MB

    def __init__(self, starting_entity_id, download_path, username=None, password=None):
        self._synapse_client = None
        self._starting_entity_id = starting_entity_id
        self._username = username
        self._password = password

        self.project = None
        self.download_view = None
        self._aiosession = None

        self.total_files = 0
        self.files_processed = 0
        self.has_errors = False

        self.start_time = None
        self.end_time = None

        var_path = os.path.expandvars(download_path)
        expanded_path = os.path.expanduser(var_path)
        self._download_path = os.path.abspath(expanded_path)
        Utils.ensure_dirs(self._download_path)

    def execute(self):
        self.start_time = datetime.now()

        self.total_files = 0
        self.files_processed = 0
        self.has_errors = False

        self._synapse_login()
        parent = self._synapse_client.get(self._starting_entity_id, downloadFile=False)
        if type(parent) not in [syn.Project, syn.Folder]:
            raise Exception('Starting entity must be a Project or Folder.')

        logging.info('Starting entity: {0} ({1})'.format(parent.name, parent.id))
        logging.info('Downloading to: {0}'.format(self._download_path))

        self.project = SynapseParentIter(self._synapse_client, parent).get_project()
        self.download_view = DownloadFileView(self._synapse_client, self.project, scope=parent).load()
        self.total_files = len(self.download_view)
        logging.info('Total files: {0}'.format(self.total_files))

        asyncio.run(self._start(parent, self._download_path))

        self.end_time = datetime.now()
        logging.info('')
        logging.info('Run time: {0}'.format(self.end_time - self.start_time))

        if self.has_errors:
            logging.error('Finished with errors. Please see log file.')
        else:
            logging.info('Finished successfully.')

    def _synapse_login(self):
        logging.info('Logging into Synapse...')
        self._username = self._username or os.getenv('SYNAPSE_USERNAME')
        self._password = self._password or os.getenv('SYNAPSE_PASSWORD')

        if not self._username:
            self._username = input('Synapse username: ')

        if not self._password:
            self._password = getpass.getpass(prompt='Synapse password: ')

        try:
            # Disable the synapseclient progress output.
            syn.utils.printTransferProgress = lambda *a, **k: None

            self._synapse_client = syn.Synapse(skip_checks=True)
            self._synapse_client.login(self._username, self._password, silent=True)
        except Exception as ex:
            self._synapse_client = None
            logging.error('Synapse login failed: {0}'.format(str(ex)))

        return self._synapse_client is not None

    async def _start(self, parent, local_path):
        try:
            self._aiosession = aiohttp.ClientSession()
            await self._download_children(parent, local_path)
        except Exception as ex:
            logging.exception(ex)
            self.has_errors = True
        finally:
            await self._aiosession.close()

    async def _download_children(self, parent, local_path):
        syn_folders = []
        syn_files = []

        for child in await self._get_children(parent):
            child_id = child.get('id')
            child_name = child.get('name')

            if child.get('type') == 'org.sagebionetworks.repo.model.Folder':
                syn_folders.append({'id': child_id, 'name': child_name, 'local_path': local_path})
            else:
                syn_files.append(child_id)

        if syn_files:
            file_handles = await self._get_filehandles(syn_files) or []
            if len(syn_files) != len(file_handles):
                parent_id = parent.id if isinstance(parent, syn.Entity) else parent
                logging.warning(
                    'Parent: {0} - Files: {1} - Handles: {2}'.format(parent_id, len(syn_files), len(file_handles)))
                raise Exception('File Handle count does not match File Count.')
            await self._download_filehandles(file_handles, local_path)

        if syn_folders:
            for syn_folder in syn_folders:
                await self._download_folder(syn_folder['id'], syn_folder['name'], syn_folder['local_path'])

    async def _get_filehandles(self, file_ids):
        uri = '/fileHandle/batch'
        endpoint = self._synapse_client.fileHandleEndpoint
        headers = None
        uri, headers = self._synapse_client._build_uri_and_headers(uri, endpoint, headers)

        # Fix the signature for aiohttp
        headers['signature'] = headers['signature'].decode("utf-8")

        results = []

        for chunk in Utils.split_chunk(file_ids, 100):
            file_handle_associations = []

            for file_id in chunk:
                view_item = self.download_view[file_id]

                file_handle_associations.append({
                    'fileHandleId': view_item.get('dataFileHandleId'),
                    'associateObjectId': view_item.get('id'),
                    'associateObjectType': 'FileEntity'
                })

            body = {
                'includeFileHandles': True,
                'includePreSignedURLs': True,
                'includePreviewPreSignedURLs': False,
                'requestedFiles': file_handle_associations}

            res = await self._restPost(uri, headers, body=body)
            results += res.get('requestedFiles', [])

        return results

    async def _restPost(self, uri, headers, body=None):
        max_attempts = 5
        attempt_number = 0
        while True:
            try:
                async with self._aiosession.post(uri, headers=headers, json=body) as response:
                    return await response.json()
            except Exception as ex:
                logging.exception(ex)
                attempt_number += 1
                if attempt_number < max_attempts:
                    sleep_time = random.randint(1, 5)
                    logging.error('  Retrying POST in: {0}'.format(sleep_time))
                    await asyncio.sleep(sleep_time)
                else:
                    self.has_errors = True
                    logging.error('  Failed POST file: {0}'.format(uri))
                    return []

    async def _download_filehandles(self, filehandles, local_path):
        for filehandle in filehandles:
            url = filehandle.get('preSignedURL')
            filename = filehandle.get('fileHandle').get('fileName')
            remote_md5 = filehandle.get('fileHandle').get('contentMd5')
            content_size = filehandle.get('fileHandle').get('contentSize')

            await self._download_file(url, filename, remote_md5, content_size, local_path)

    async def _download_file(self, url, name, remote_md5, remote_size, local_path):
        self.files_processed += 1
        full_path = os.path.join(local_path, name)
        logging.info('File  : {0} -> {1} [{2} of {3}]'.format(full_path.replace(self._download_path, ''),
                                                              full_path,
                                                              self.files_processed,
                                                              self.total_files))

        if os.path.isfile(full_path):
            logging.info('  File exists, checking MD5...')
            local_md5 = await self._get_md5(full_path)
            if local_md5 == remote_md5:
                logging.info('  Local file matches remote file. Skipping...')
                return None
            else:
                logging.info('  Local file does not match remote file. Downloading...')

        max_attempts = 5
        attempt_number = 0
        while True:
            try:
                async with self._aiosession.get(url) as response:
                    async with aiofiles.open(full_path, mode='wb') as fd:
                        chunk_size_read = 0
                        while True:
                            chunk = await response.content.read(self.CHUNK_SIZE)
                            if not chunk:
                                break
                            chunk_size_read += len(chunk)
                            sys.stdout.write('\r')
                            sys.stdout.flush()
                            sys.stdout.write('  Saving chunk {0} of {1}'.format(chunk_size_read, remote_size))
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
                    self.has_errors = True
                    logging.error('  Failed to download file: {0}'.format(full_path))
                    break

    async def _get_md5(self, local_path):
        md5 = hashlib.md5()
        async with aiofiles.open(local_path, mode='rb') as fd:
            while True:
                chunk = await fd.read(self.CHUNK_SIZE)
                if not chunk:
                    break
                md5.update(chunk)
        return md5.hexdigest()

    async def _get_children(self, parent):
        args = partial(self._synapse_client.getChildren,
                       parent=parent,
                       includeTypes=["folder", "file"])

        result = await asyncio.get_running_loop().run_in_executor(None, args)

        return list(result)

    async def _get_entity(self, id, download_file=False):
        args = partial(self._synapse_client.get,
                       entity=id,
                       downloadFile=download_file)

        return await asyncio.get_running_loop().run_in_executor(None, args)

    async def _download_folder(self, syn_id, name, local_path):
        full_path = os.path.join(local_path, name)
        logging.info('Folder: {0} -> {1}'.format(full_path.replace(self._download_path, ''), full_path))
        Utils.ensure_dirs(full_path)
        await self._download_children(syn_id, full_path)
