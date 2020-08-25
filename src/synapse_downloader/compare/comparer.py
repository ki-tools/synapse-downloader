import os
import logging
import synapseclient as syn
from datetime import datetime
from ..core import Utils, SynapseProxy, AioManager
from ..download import FileHandleView


class Comparer:

    def __init__(self, starting_entity_id, local_path, with_view=False, ignores=None, username=None, password=None):
        self._starting_entity_id = starting_entity_id
        self._local_path = Utils.expand_path(local_path)
        self._with_view = with_view
        self._ignores = []
        for ignore in (ignores or []):
            if ignore.lower().strip().startswith('syn'):
                self._ignores.append(ignore.lower().strip())
            else:
                self._ignores.append(Utils.expand_path(ignore))

        self._username = username
        self._password = password

        self._file_handle_view = None

        self.start_time = None
        self.end_time = None
        self.total_remote_files = None
        self.remote_files_processed = 0
        self.has_errors = False

    def start(self):
        self.total_remote_files = None
        self.remote_files_processed = 0
        self.has_errors = False

        if SynapseProxy.logged_in() or SynapseProxy.login(username=self._username, password=self._password):
            AioManager.start(self._startAsync)
        else:
            self.has_errors = True

        self.end_time = datetime.now()
        self._log_info('Run time: {0}'.format(self.end_time - (self.start_time or datetime.now())))

        if self.has_errors:
            logging.error('Finished with errors. See log file.')
        else:
            logging.info('Finished successfully.')

    async def _startAsync(self):
        try:
            start_entity = await SynapseProxy.getAsync(self._starting_entity_id, downloadFile=False)

            if type(start_entity) not in [syn.Project, syn.Folder, syn.File]:
                raise Exception('Starting entity must be a Project, Folder, or File.')

            logging.info('Starting Compare Entity: {0} ({1})'.format(start_entity.name, start_entity.id))
            logging.info('Comparing to: {0}'.format(self._local_path))
            if self._ignores:
                logging.info('Ignoring: {0}'.format(', '.join(self._ignores)))

            self._file_handle_view = FileHandleView(start_entity)

            if self._with_view:
                await self._file_handle_view.load()
                self.total_remote_files = len(self._file_handle_view)
                logging.info('Total Remote files: {0}'.format(self.total_remote_files))

            self.start_time = datetime.now()

            if isinstance(start_entity, syn.File):
                parent = await SynapseProxy.getAsync(start_entity.parentId)
                await self._check_path(parent, self._local_path, remote_file=start_entity)
            else:
                await self._check_path(start_entity, self._local_path)
        except Exception as ex:
            logging.exception(ex)
            self._log_error('Unknown error. See log file.')

    def _log_error(self, *msg):
        self.has_errors = True
        logging.error('\n'.join(msg))

    def _log_info(self, *msg):
        logging.info('\n'.join(msg))

    async def _check_path(self, parent, local_path, remote_file=None):
        if os.path.isdir(local_path):
            remote_file_filename = remote_file.get('_file_handle').get('fileName') if remote_file else None

            local_dirs, local_files = self._get_local_dirs_and_files(local_path, filename=remote_file_filename)
        else:
            local_dirs, local_files = [[], []]

        remote_dirs, remote_files = await self._get_remote_dirs_and_files(parent, remote_file=remote_file)

        for remote_file in remote_files:
            self.remote_files_processed += 1
            progress_msg = str(self.remote_files_processed)
            if self.total_remote_files is not None:
                progress_msg += ' of {0}'.format(self.total_remote_files)

            local_match = self._find_by_name(local_files, remote_file['name'])

            if (remote_file['id'] in self._ignores) or (local_match and local_match.path in self._ignores):
                self._log_info('[SKIPPING REMOTE FILE]',
                               '  REMOTE [ ]: {0}({1})'.format(remote_file['name'], remote_file['id']),
                               '')

                if local_match:
                    self._log_info('[SKIPPING LOCAL FILE]',
                                   '  LOCAL  [ ]: {0}'.format(local_match.path),
                                   '')
                    local_files.remove(local_match)
                continue

            if local_match:
                local_files.remove(local_match)

                self._log_info('[LOCAL FILE FOUND] [{0}]'.format(progress_msg),
                               '  REMOTE [+]: {0}({1})'.format(remote_file['name'], remote_file['id']),
                               '  LOCAL  [+]: {0}'.format(local_match.path),
                               '')

                remote_size = remote_file['content_size']
                local_size = os.path.getsize(local_match.path)
                # NOTE: For ExternalFileHandles the size and MD5 data will not be present.
                is_unknown_size = remote_size is None

                if is_unknown_size:
                    # TODO: Should we download the ExternalFileHandle and check its size?
                    self._log_info('[REMOTE SIZE UNKNOWN]',
                                   '  REMOTE [?]: {0}({1}) ({2})'.format(remote_file['name'],
                                                                         remote_file['id'],
                                                                         Utils.pretty_size(remote_size)),
                                   '  LOCAL  [+]: {0} ({1})'.format(local_match.path, Utils.pretty_size(local_size)),
                                   '')
                elif local_size != remote_size:
                    self._log_error('[SIZE MISMATCH]',
                                    '  REMOTE [-]: {0}({1}) ({2})'.format(remote_file['name'],
                                                                          remote_file['id'],
                                                                          Utils.pretty_size(remote_size)),
                                    '  LOCAL  [-]: {0} ({1})'.format(local_match.path, Utils.pretty_size(local_size)),
                                    '')
                else:
                    remote_md5 = remote_file['content_md5']
                    local_md5 = await Utils.get_md5(local_match.path)
                    if local_md5 != remote_md5:
                        self._log_error('[MD5 MISMATCH]',
                                        '  REMOTE [-]: {0}({1}) ({2})'.format(remote_file['name'],
                                                                              remote_file['id'],
                                                                              remote_md5),
                                        '  LOCAL  [-]: {0} ({1})'.format(local_match.path, local_md5),
                                        '')

            else:
                self._log_error('[LOCAL FILE NOT FOUND] [{0}]'.format(progress_msg),
                                '  REMOTE [+]: {0}({1})'.format(remote_file['name'], remote_file['id']),
                                '  LOCAL  [-]: {0}'.format(os.path.join(local_path, remote_file['name'])),
                                '')

        for remote_dir in remote_dirs:
            local_match = self._find_by_name(local_dirs, remote_dir['name'])

            if (remote_dir['id'] in self._ignores) or (local_match and local_match.path in self._ignores):
                self._log_info('[SKIPPING REMOTE DIRECTORY]',
                               '  REMOTE [ ]: {0}({1})'.format(remote_dir['name'], remote_dir['id']),
                               '')

                if local_match:
                    self._log_info('[SKIPPING LOCAL DIRECTORY]',
                                   '  LOCAL  [ ]: {0}'.format(local_match.path),
                                   '')
                    local_dirs.remove(local_match)
                continue

            if local_match:
                local_dirs.remove(local_match)

                self._log_info('[LOCAL DIRECTORY FOUND]',
                               '  REMOTE [+]: {0}({1})'.format(remote_dir['name'], remote_dir['id']),
                               '  LOCAL  [+]: {0}'.format(local_match.path),
                               '')

                await self._check_path(remote_dir, os.path.join(local_path, remote_dir['name']))
            else:
                self._log_error('[LOCAL DIRECTORY NOT FOUND]',
                                '  REMOTE [+]: {0}({1})'.format(remote_dir['name'], remote_dir['id']),
                                '  LOCAL  [-]: {0}'.format(os.path.join(local_path, remote_dir['name'])),
                                '')

        for local_file in local_files:
            remote_match = self._find_by_name(remote_files, local_file.name)

            if (local_file.path in self._ignores) or (remote_match and remote_match['id'] in self._ignores):
                self._log_info('[SKIPPING LOCAL FILE]',
                               '  LOCAL  [ ]: {0}'.format(local_file.path),
                               '')

                if remote_match:
                    self._log_info('[SKIPPING REMOTE FILE]',
                                   '  REMOTE [ ]: {0}({1})'.format(remote_match['name'], remote_match['id']),
                                   '')
                    remote_files.remove(remote_match)
                continue

            if remote_match:
                remote_files.remove(remote_match)
                self._log_info('[REMOTE FILE FOUND]',
                               '  LOCAL  [+]: {0}'.format(local_file.path),
                               '  REMOTE [+]: {0}({1})/{2}'.format(parent['name'], parent['id'], local_file.name),
                               '')
            else:
                self._log_error('[REMOTE FILE NOT FOUND]',
                                '  LOCAL  [+]: {0}'.format(local_file.path),
                                '  REMOTE [-]: {0}({1})/{2}'.format(parent['name'], parent['id'], local_file.name),
                                '')

        for local_dir in local_dirs:
            remote_match = self._find_by_name(remote_dirs, local_dir.name)

            if (local_dir.path in self._ignores) or (remote_match and remote_match['id'] in self._ignores):
                self._log_info('[SKIPPING LOCAL DIRECTORY]',
                               '  LOCAL  [ ]: {0}'.format(local_dir.path),
                               '')

                if remote_match:
                    self._log_info('[SKIPPING REMOTE DIRECTORY]',
                                   '  REMOTE [ ]: {0}({1})'.format(remote_match['name'], remote_match['id']),
                                   '')
                    remote_dirs.remove(remote_match)
                continue

            if remote_match:
                remote_dirs.remove(remote_match)
                self._log_info('[REMOTE DIRECTORY FOUND]',
                               '  LOCAL  [+]: {0}'.format(local_dir.path),
                               '  REMOTE [+]: {0}/{1}({2})'.format(parent['name'],
                                                                   remote_match['name'],
                                                                   remote_match['id']),
                               '')

                await self._check_path(remote_match, os.path.join(local_path, remote_match['name']))
            else:
                self._log_error('[REMOTE DIRECTORY NOT FOUND]',
                                '  LOCAL  [+]: {0}'.format(local_dir.path),
                                '  REMOTE [-]: {0}({1})/{2}'.format(parent['name'], parent['id'], local_dir.name),
                                '')

    def _find_by_name(self, _list, name):
        """Finds an item by its name property in a list.

        Args:
            _list: The list (dicts, syn.Files, or syn.Folders) to search.
            name: The name to search by.

        Returns:
            The matching list item or None.

        Raises:
            Exception if more than one item in the list matches the name.
        """

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

    def _get_local_dirs_and_files(self, local_path, filename=None):
        """Gets all the directories and files in a local path, or a specific file by its name.

        Args:
            local_path: The local path to get files and folders for.
            filename: The name of a single file to return in local_path (if it exists). If present then only
                      this file will be returned in the files list.

        Returns:
            List of directory paths, List of file paths.
        """
        dirs = []
        files = []

        entries = list(os.scandir(local_path))
        for entry in entries:
            # Do not follow any sym links.
            if entry.is_symlink():
                continue

            if filename:
                if entry.is_file() and entry.name == filename:
                    files.append(entry)
                    break
            else:
                if entry.is_dir():
                    dirs.append(entry)
                else:
                    files.append(entry)

        dirs.sort(key=lambda f: f.name)
        files.sort(key=lambda f: f.name)

        return dirs, files

    async def _get_remote_dirs_and_files(self, parent, remote_file=None):
        """Gets all the directories and files in a remote parent (Project or Folder), or a specific remote file.

        Args:
            parent: The remote project or folder to get directories and files for.
            remote_file: The only remote File to return. If present then only this file is returned in the files list.

        Returns:
            List of dicts with folder attributes, List of dicts with file attributes.
        """
        remote_dirs = []
        remote_files = []

        async def _add_child(id, name, is_file=False):
            entity = {
                'id': id,
                'name': name
            }
            if is_file:
                filehandle = await self._file_handle_view.get_filehandle(id)
                entity['name'] = filehandle.get('fileHandle').get('fileName')
                entity['content_md5'] = filehandle.get('fileHandle').get('contentMd5')
                entity['content_size'] = filehandle.get('fileHandle').get('contentSize')
                remote_files.append(entity)
            else:
                remote_dirs.append(entity)

        if remote_file:
            await _add_child(remote_file.id, remote_file.name, is_file=True)
        else:
            async for child in SynapseProxy.Aio.get_children(parent, includeTypes=["folder", "file"]):
                is_file = child.get('type') == 'org.sagebionetworks.repo.model.FileEntity'
                await _add_child(child.get('id'), child.get('name'), is_file=is_file)

        return remote_dirs, remote_files
