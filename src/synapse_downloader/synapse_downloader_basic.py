import os
import logging
from datetime import datetime
import synapseclient as syn
from .aio_manager import AioManager
from .utils import Utils
from .synapse_proxy import SynapseProxy
from .download_view import DownloadView


class SynapseDownloaderBasic:

    def __init__(self, starting_entity_id, download_path, with_view=False, username=None, password=None):
        self._starting_entity_id = starting_entity_id
        self._with_view = with_view
        self._username = username
        self._password = password

        self.start_time = None
        self.end_time = None

        self._download_view = None
        self.total_files = None
        self.files_processed = 0
        self.has_errors = False

        var_path = os.path.expandvars(download_path)
        expanded_path = os.path.expanduser(var_path)
        self._download_path = os.path.abspath(expanded_path)

    def start(self):
        self.total_files = None
        self.files_processed = 0
        self.has_errors = False

        if SynapseProxy.login(username=self._username, password=self._password):
            AioManager.start(self._startAsync)
        else:
            self.has_errors = True

        self.end_time = datetime.now()
        logging.info('')
        logging.info('Run time: {0}'.format(self.end_time - self.start_time))

        if self.has_errors:
            logging.error('Finished with errors. Please see log file.')
        else:
            logging.info('Finished successfully.')

    async def _startAsync(self):
        try:
            Utils.ensure_dirs(self._download_path)

            parent = await SynapseProxy.getAsync(self._starting_entity_id, downloadFile=False)

            if type(parent) not in [syn.Project, syn.Folder]:
                raise Exception('Starting entity must be a Project or Folder.')

            self._download_view = DownloadView(parent)

            if self._with_view:
                await self._download_view.load()
                self.total_files = len(self._download_view)
                logging.info('Total files: {0}'.format(self.total_files))

            logging.info('Starting entity: {0} ({1})'.format(parent.name, parent.id))
            logging.info('Downloading to: {0}'.format(self._download_path))

            self.start_time = datetime.now()
            await self._download_children(parent, self._download_path)
        except Exception as ex:
            logging.exception(ex)
            self.has_errors = True

    async def _download_children(self, parent, local_path):
        syn_folders = []

        async for child in SynapseProxy.Aio.get_children(parent, includeTypes=["folder", "file"]):
            child_id = child.get('id')
            child_name = child.get('name')

            if child.get('type') == 'org.sagebionetworks.repo.model.Folder':
                syn_folders.append({'id': child_id, 'name': child_name, 'local_path': local_path})
            else:
                await self._download_file(child_id, local_path)

        if syn_folders:
            for syn_folder in syn_folders:
                await self._download_folder(syn_folder['id'], syn_folder['name'], syn_folder['local_path'])

    async def _download_folder(self, syn_id, name, local_path):
        full_path = os.path.join(local_path, name)
        logging.info('Folder: {0} -> {1}'.format(full_path.replace(self._download_path, ''), full_path))
        Utils.ensure_dirs(full_path)
        await self._download_children(syn_id, full_path)

    async def _download_file(self, syn_id, local_path):
        try:
            filehandle = await self._download_view.get_filehandle(syn_id)

            url = filehandle.get('preSignedURL')
            filename = filehandle.get('fileHandle').get('fileName')
            remote_md5 = filehandle.get('fileHandle').get('contentMd5')
            content_size = filehandle.get('fileHandle').get('contentSize')

            full_path = os.path.join(local_path, filename)

            progress_msg = str(self.files_processed + 1)
            if self.total_files is not None:
                progress_msg += ' of {0}'.format(self.total_files)

            logging.info(
                'File  : {0} -> {1} [{2}]'.format(full_path.replace(self._download_path, ''), full_path, progress_msg))

            can_download = True

            if os.path.isfile(full_path):
                local_md5 = await Utils.get_md5(full_path)
                if local_md5 == remote_md5:
                    can_download = False
                    logging.info('File is current.')

            if can_download:
                await SynapseProxy.Aio.download_file(url, full_path, content_size)
        except Exception as ex:
            self.has_errors = True
            logging.exception(ex)
            
        self.files_processed += 1
