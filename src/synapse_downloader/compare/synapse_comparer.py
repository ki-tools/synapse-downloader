import os
import logging
import synapseclient as syn
from datetime import datetime
from ..utils import Utils
from ..synapse_proxy import SynapseProxy
from ..aio_manager import AioManager
from ..file_handle_view import FileHandleView


class SynapseComparer:
    def __init__(self, remote_id, local_path, with_view=False, username=None, password=None):
        self._local_path = Utils.expand_path(local_path)
        self._remote_id = remote_id
        self._with_view = with_view
        self._username = username
        self._password = password

        self._file_handle_view = None

        self.start_time = None
        self.end_time = None
        self.total_files = None
        self.has_errors = False
        self.files_processed = 0

    def start(self):
        self.has_errors = False
        self.files_processed = 0

        if SynapseProxy.login(username=self._username, password=self._password):
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
            parent = await SynapseProxy.getAsync(self._remote_id, downloadFile=False)

            if type(parent) not in [syn.Project, syn.Folder]:
                raise Exception('Remote entity must be a Project or Folder.')

            logging.info('Remote Entity: {0} ({1})'.format(parent.name, parent.id))
            logging.info('Local Path: {0}'.format(self._local_path))

            self._file_handle_view = FileHandleView(parent)

            if self._with_view:
                await self._file_handle_view.load()
                self.total_files = len(self._file_handle_view)
                logging.info('Total files: {0}'.format(self.total_files))

            self.start_time = datetime.now()
            await self._check_path(parent, self._local_path)
        except Exception as ex:
            logging.exception(ex)
            self.has_errors = True

    def _add_error(self, msg):
        self.has_errors = True
        logging.error(msg)

    async def _check_path(self, parent, local_path):
        local_dirs, local_files = Utils.get_dirs_and_files(local_path) if os.path.isdir(local_path) else [[], []]
        remote_dirs, remote_files = await self._get_remote_dirs_and_files(parent)

        for remote_dir in remote_dirs:
            local_match = self._find_by_name(local_dirs, remote_dir['name'])
            if not local_match:
                err_strs = ['[LOCAL DIRECTORY NOT FOUND]']
                err_strs.append('  REMOTE [+]: {0}({1})'.format(remote_dir['name'], remote_dir['id']))
                err_strs.append('  LOCAL  [ ]: {0}'.format(os.path.join(local_path, remote_dir['name'])))
                self._add_error(os.linesep.join(err_strs))

        for local_dir in local_dirs:
            remote_match = self._find_by_name(remote_dirs, local_dir.name)
            if not remote_match:
                err_strs = ['[REMOTE DIRECTORY NOT FOUND]']
                err_strs.append('  LOCAL  [+]: {0}'.format(local_dir.path))
                err_strs.append('  REMOTE [ ]: {0}({1})/{2}'.format(parent['name'], parent['id'], local_dir.name))
                self._add_error(os.linesep.join(err_strs))

        for remote_file in remote_files:
            local_match = self._find_by_name(local_files, remote_file['name'])
            if local_match:
                remote_size = remote_file['content_size']
                local_size = os.path.getsize(local_match.path)
                if local_size != remote_size:
                    err_strs = ['[SIZE MISMATCH]']
                    err_strs.append('  REMOTE [{0}]: {1}({2})'.format(remote_size,
                                                                      remote_file['name'],
                                                                      remote_file['id']))
                    err_strs.append('  LOCAL  [{0}]: {1}'.format(local_size, local_match.path))
                    self._add_error(os.linesep.join(err_strs))
                else:
                    remote_md5 = remote_file['content_md5']
                    local_md5 = await Utils.get_md5(local_match.path)
                    if local_md5 != remote_md5:
                        err_strs = ['[MD5 MISMATCH]']
                        err_strs.append('  REMOTE [{0}]: {1}({2})'.format(remote_md5,
                                                                          remote_file['name'],
                                                                          remote_file['id']))
                        err_strs.append('  LOCAL  [{0}]: {1}'.format(local_md5, local_match.path))
                        self._add_error(os.linesep.join(err_strs))
            else:
                err_strs = ['[LOCAL FILE NOT FOUND]']
                err_strs.append('  REMOTE [+]: {0}({1})'.format(remote_file['name'], remote_file['id']))
                err_strs.append('  LOCAL  [ ]: {0}'.format(os.path.join(local_path, remote_file['name'])))
                self._add_error(os.linesep.join(err_strs))

        for local_file in local_files:
            remote_match = self._find_by_name(remote_files, local_file.name)
            if not remote_match:
                err_strs = ['[REMOTE FILE NOT FOUND]']
                err_strs.append('  LOCAL  [+]: {0}'.format(local_file.path))
                err_strs.append('  REMOTE [ ]: {0}({1})/{2}'.format(parent['name'], parent['id'], local_file.name))
                self._add_error(os.linesep.join(err_strs))

            self.files_processed += 1
            if self.files_processed % 100 == 0:
                progress_msg = str(self.files_processed)
                if self.total_files is not None:
                    progress_msg += ' of {0}'.format(self.total_files)
                logging.info('Processed Files: {0}'.format(progress_msg))

        # Check the child folders.
        for remote_dir in remote_dirs:
            await self._check_path(remote_dir, os.path.join(local_path, remote_dir['name']))

    def _find_by_name(self, _list, name):
        results = []

        if len(_list) and isinstance(_list[-1], dict):
            results = [item for item in _list if item['name'] == name]
        else:
            results = [item for item in _list if item.name == name]

        if len(results) > 1:
            raise Exception('More than one item found matching name: {0}'.format(name))
        elif len(results):
            return results[-1]
        else:
            return None

    async def _get_remote_dirs_and_files(self, parent):
        remote_dirs = []
        remote_files = []

        async for child in SynapseProxy.Aio.get_children(parent, includeTypes=["folder", "file"]):
            entity = {
                'id': child.get('id'),
                'name': child.get('name')
            }

            if child.get('type') == 'org.sagebionetworks.repo.model.Folder':
                remote_dirs.append(entity)
            else:
                filehandle = await self._file_handle_view.get_filehandle(child.get('id'))
                entity['name'] = filehandle.get('fileHandle').get('fileName')
                entity['content_md5'] = filehandle.get('fileHandle').get('contentMd5')
                entity['content_size'] = filehandle.get('fileHandle').get('contentSize')
                remote_files.append(entity)

        return remote_dirs, remote_files
