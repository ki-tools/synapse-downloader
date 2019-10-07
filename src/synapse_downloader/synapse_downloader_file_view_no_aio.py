import os
import sys
import getpass
import synapseclient as syn
import requests
import logging
from datetime import datetime
import hashlib
from .utils import Utils
from .syn_parent_iter import SynapseParentIter
from .download_file_view import DownloadFileView


class SynapseDownloaderFileViewNoAio:
    MB = 2 ** 20
    CHUNK_SIZE = 10 * MB

    def __init__(self, starting_entity_id, download_path, username=None, password=None):
        self._synapse_client = None
        self._starting_entity_id = starting_entity_id
        self._username = username
        self._password = password

        self.project = None
        self.download_view = None

        self.start_time = None
        self.end_time = None

        var_path = os.path.expandvars(download_path)
        expanded_path = os.path.expanduser(var_path)
        self._download_path = expanded_path
        Utils.ensure_dirs(self._download_path)

    def synapse_login(self):
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

    def execute(self):
        self.start_time = datetime.now()

        self.synapse_login()
        parent = self._synapse_client.get(self._starting_entity_id, downloadFile=False)
        if type(parent) not in [syn.Project, syn.Folder]:
            raise Exception('Starting entity must be a Project or Folder.')

        logging.info('Starting entity: {0} ({1})'.format(parent.name, parent.id))
        logging.info('Downloading to: {0}'.format(self._download_path))

        self.project = SynapseParentIter(self._synapse_client, parent).get_project()
        self.download_view = DownloadFileView(self._synapse_client, self.project, parent).load()

        self._start(parent, self._download_path)

        self.end_time = datetime.now()
        logging.info('')
        logging.info('Run time: {0}'.format(self.end_time - self.start_time))

    def _start(self, parent, local_path):
        try:
            self._download_children(parent, local_path)
        except Exception as ex:
            logging.exception(ex)
        finally:
            pass

    def _download_children(self, parent, local_path):
        syn_folders = []
        syn_files = []

        for child in self._get_children(parent):
            child_id = child.get('id')
            child_name = child.get('name')

            if child.get('type') == 'org.sagebionetworks.repo.model.Folder':
                syn_folders.append({'id': child_id, 'name': child_name, 'local_path': local_path})
            else:
                syn_files.append(child_id)

        if syn_files:
            file_handles = self._get_filehandles(syn_files) or []
            if len(syn_files) != len(file_handles):
                parent_id = parent.id if isinstance(parent, syn.Entity) else parent
                logging.warning(
                    'Parent: {0} - Files: {1} - Handles: {2}'.format(parent_id, len(syn_files), len(file_handles)))
                raise Exception('File Handle count does not match File Count.')
            self._download_filehandles(file_handles, local_path)

        if syn_folders:
            for syn_folder in syn_folders:
                self._download_folder(syn_folder['id'], syn_folder['name'], syn_folder['local_path'])

    def _get_filehandles(self, file_ids):
        uri = '/fileHandle/batch'
        endpoint = self._synapse_client.fileHandleEndpoint
        headers = None
        uri, headers = self._synapse_client._build_uri_and_headers(uri, endpoint, headers)

        # Fix the signature
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

            res = self._restPost(uri, headers, body=body)
            results += res.get('requestedFiles', [])

        return results

    def _restPost(self, uri, headers, body=None):
        with requests.post(uri, headers=headers, json=body) as response:
            return response.json()

    def _download_filehandles(self, filehandles, local_path):
        for filehandle in filehandles:
            url = filehandle.get('preSignedURL')
            filename = filehandle.get('fileHandle').get('fileName')
            remote_md5 = filehandle.get('fileHandle').get('contentMd5')
            content_size = filehandle.get('fileHandle').get('contentSize')

            self._download_file(url, filename, remote_md5, content_size, local_path)

    def _download_file(self, url, name, remote_md5, remote_size, local_path):
        full_path = os.path.join(local_path, name)
        logging.info('File  : {0} -> {1}'.format('--', full_path))

        if os.path.isfile(full_path):
            logging.info('  File exists, checking MD5...')
            local_md5 = self._get_md5(full_path)
            if local_md5 == remote_md5:
                logging.info('  Local file matches remote file. Skipping...')
                return None
            else:
                logging.info('  Local file does not match remote file. Downloading...')

        with requests.get(url, stream=True) as response:
            with open(full_path, mode='wb') as fd:
                chunk_size_read = 0
                for chunk in response.iter_content(chunk_size=self.CHUNK_SIZE):
                    if chunk:
                        chunk_size_read += len(chunk)
                        sys.stdout.write('\r')
                        sys.stdout.flush()
                        sys.stdout.write('  Saving chunk {0} of {1}'.format(chunk_size_read, remote_size))
                        sys.stdout.flush()
                        fd.write(chunk)
                print('')
                logging.info('  Saved {0} bytes'.format(chunk_size_read))

    def _get_md5(self, local_path):
        md5 = hashlib.md5()
        with open(local_path, mode='rb') as fd:
            while True:
                chunk = fd.read(self.CHUNK_SIZE)
                if not chunk:
                    break
                md5.update(chunk)
        return md5.hexdigest()

    def _get_children(self, parent):
        return list(self._synapse_client.getChildren(parent=parent, includeTypes=["folder", "file"]))

    def _get_entity(self, id, download_file=False):
        return self._synapse_client.get(id, downloadFile=download_file)

    def _download_folder(self, syn_id, name, local_path):
        full_path = os.path.join(local_path, name)
        logging.info('Folder: {0} -> {1}'.format(syn_id, full_path))
        Utils.ensure_dirs(full_path)
        self._download_children(syn_id, full_path)
