import os
import logging
from datetime import datetime
import synapseclient as syn
from ..core import Utils, AioManager, SynapseProxy
from .file_handle_view import FileHandleView


class Downloader:

    def __init__(self, starting_entity_id, download_path, excludes=None, with_view=False, username=None, password=None):
        self._starting_entity_id = starting_entity_id
        self._download_path = Utils.expand_path(download_path)
        self._with_view = with_view
        self._username = username
        self._password = password
        self._excludes = []
        for exclude in (excludes or []):
            if exclude.lower().strip().startswith('syn'):
                self._excludes.append(exclude.lower().strip())
            else:
                self._excludes.append(exclude)

        self.start_time = None
        self.end_time = None

        self._file_handle_view = None
        self.total_files = None
        self.files_processed = 0
        self.has_errors = False

    def start(self):
        self.total_files = None
        self.files_processed = 0
        self.has_errors = False

        if SynapseProxy.logged_in() or SynapseProxy.login(username=self._username, password=self._password):
            AioManager.start(self._startAsync)
        else:
            self.has_errors = True

        self.end_time = datetime.now()
        logging.info('')
        logging.info('Run time: {0}'.format(self.end_time - (self.start_time or datetime.now())))

        if self.has_errors:
            logging.error('Finished with errors. Please see log file.')
        else:
            logging.info('Finished successfully.')

    async def _startAsync(self):
        try:
            Utils.ensure_dirs(self._download_path)

            start_entity = await SynapseProxy.getAsync(self._starting_entity_id, downloadFile=False)

            if type(start_entity) not in [syn.Project, syn.Folder, syn.File]:
                raise Exception('Starting entity must be a Project, Folder, or File.')

            logging.info('Starting Download Entity: {0} ({1})'.format(start_entity.name, start_entity.id))
            logging.info('Downloading to: {0}'.format(self._download_path))
            if self._excludes:
                logging.info('Excluding: {0}'.format(','.join(self._excludes)))

            self._file_handle_view = FileHandleView(start_entity)

            if self._with_view:
                await self._file_handle_view.load()
                self.total_files = len(self._file_handle_view)
                logging.info('Total files: {0}'.format(self.total_files))

            self.start_time = datetime.now()

            if isinstance(start_entity, syn.File):
                await self._download_file(start_entity.id, self._download_path)
            else:
                await self._download_children(start_entity, self._download_path)
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

        for syn_folder in syn_folders:
            await self._download_folder(syn_folder['id'], syn_folder['name'], syn_folder['local_path'])

    async def _download_folder(self, syn_id, name, local_path):
        full_path = os.path.join(local_path, name)
        full_remote_path = full_path.replace(self._download_path, '')

        if syn_id in self._excludes or \
                name in self._excludes or \
                full_remote_path in self._excludes:
            logging.info('Skipping Folder: {0} ({1})'.format(full_remote_path, syn_id))
        else:
            logging.info('Folder: {0} -> {1}'.format(full_remote_path, full_path))
            Utils.ensure_dirs(full_path)
            await self._download_children(syn_id, full_path)

    async def _download_file(self, syn_id, local_path):
        try:
            filehandle = await self._file_handle_view.get_filehandle(syn_id)

            filename = filehandle.get('fileHandle').get('fileName')
            remote_md5 = filehandle.get('fileHandle').get('contentMd5')
            content_size = filehandle.get('fileHandle').get('contentSize')
            # NOTE: For ExternalFileHandles the size and MD5 data will not be present.
            is_unknown_size = content_size is None

            full_path = os.path.join(local_path, filename)
            full_remote_path = full_path.replace(self._download_path, '')

            progress_msg = str(self.files_processed + 1)
            if self.total_files is not None:
                progress_msg += ' of {0}'.format(self.total_files)

            # Only fetch the entity name if there are excludes since this adds time.
            excludable_name = None
            if self._excludes:
                view_data = await self._file_handle_view.get(syn_id)
                excludable_name = view_data[FileHandleView.COL_NAME]

            if syn_id in self._excludes or \
                    filename in self._excludes or \
                    full_remote_path in self._excludes or \
                    (excludable_name is not None and excludable_name in self._excludes):
                logging.info('Skipping File: {0} ({1})'.format(full_remote_path, syn_id))
            else:
                logging.info(
                    'File  : {0} -> {1} [{2}]'.format(full_remote_path, full_path, progress_msg))

                can_download = True

                if is_unknown_size:
                    logging.info('External File, cannot determine changes. Force downloading...')
                elif os.path.isfile(full_path) and os.path.getsize(full_path) == content_size:
                    # Only check the md5 if the file sizes match.
                    # This way we can avoid MD5 checking for partial downloads and changed files.
                    local_md5 = await Utils.get_md5(full_path)
                    if local_md5 == remote_md5:
                        can_download = False
                        logging.info('File is current.')

                if can_download:
                    await SynapseProxy.Aio.download_file(syn_id,
                                                         full_path,
                                                         filehandle,
                                                         self._file_handle_view.get_filehandle)
        except Exception as ex:
            self.has_errors = True
            logging.exception(ex)

        self.files_processed += 1
