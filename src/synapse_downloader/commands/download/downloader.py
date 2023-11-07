import os
import logging
from datetime import datetime
import asyncio
import synapseclient as syn
from synapse_downloader.core import Utils, SynapseItem, Env, SynToolsError, FileSizeMismatchError
from synapsis import Synapsis


class Downloader:

    def __init__(self, starting_entity_id, download_path, download=True, compare=False, excludes=None):
        self._starting_entity_id = starting_entity_id
        self._download_path = Utils.expand_path(download_path)
        self._do_download = download
        self._do_compare = compare
        self._excludes = []
        for exclude in (excludes or []):
            if exclude.lower().strip().startswith('syn'):
                self._excludes.append(exclude.lower().strip())
            else:
                self._excludes.append(exclude)

        self.start_time = None
        self.end_time = None

        self.queue = None
        self.comparables = []
        self.errors = []
        self._abort = False

    def abort(self):
        self._abort = True
        self._log_error('User Aborted. Shutting down...')

    async def execute(self):
        self.start_time = datetime.now()
        self.end_time = None
        self.errors = []
        self.comparables = []
        try:
            start_entity = await Synapsis.Chain.get(self._starting_entity_id, downloadFile=False)
            start_item = await SynapseItem(
                start_entity,
                synapse_root_path=await self._remote_abs_base_path(start_entity.parentId),
                local_root_path=self._download_path
            ).load()

            if self._do_download:
                if start_item.is_file:
                    Utils.ensure_dirs(start_item.local.dirname)
                else:
                    Utils.ensure_dirs(start_item.local.abs_path)

            if self._do_compare:
                self._add_comparable(start_item)

            if not self.validate_for_download_or_compare(start_item):
                return
            if self._do_compare and not self.validate_for_compare(start_item):
                return

            if self._do_download:
                logging.info('Downloading: {0} ({1}) to {2}'.format(start_item.name,
                                                                    start_item.id,
                                                                    start_item.local.abs_path))
            if self._do_compare:
                logging.info('Comparing: {0} to {1} ({2})'.format(start_item.local.abs_path,
                                                                  start_item.name,
                                                                  start_item.id))

            if self._excludes:
                logging.info('Excluding: {0}'.format(','.join(self._excludes)))

            if Env.SYNTOOLS_SYN_GET_DOWNLOAD():
                logging.info('Using synapseclient.get for downloads.')

            if self._do_download:
                logging.info('Starting Download Process...')
            else:
                logging.info('Gathering Compare Items...')

            self.queue = asyncio.Queue()

            producers = [asyncio.create_task(self._process_children(start_item))]
            worker_count = Env.SYNTOOLS_DOWNLOAD_WORKERS()
            logging.debug('Worker Count: {0}'.format(worker_count))
            workers = [asyncio.create_task(self._worker()) for _ in range(worker_count)]
            await asyncio.gather(*producers)
            if not self._abort:
                await self.queue.join()
            for worker in workers:
                worker.cancel()

            if self._do_compare and not self._abort:
                logging.info('Starting Compare Process...')
                producers = [asyncio.create_task(self._compare_path(start_item))]
                workers = [asyncio.create_task(self._compare_worker()) for _ in range(worker_count)]
                await asyncio.gather(*producers)
                if not self._abort:
                    await self.queue.join()
                for worker in workers:
                    worker.cancel()

        except Exception as ex:
            self._log_error('Execute Error', error=ex)

        self.end_time = datetime.now()
        logging.info('')
        logging.info('Run time: {0}'.format(self.end_time - self.start_time))
        return self

    def validate_for_download_or_compare(self, start_item):
        if not (start_item.is_project or start_item.is_folder or start_item.is_file):
            self._log_error('Starting entity must be a Project, Folder, or File.')
            return False
        return True

    def validate_for_compare(self, start_item):
        if not start_item.local.exists and not self._do_download:
            self._log_error('Local path does not exist: {0}'.format(start_item.local.abs_path))
            return False

        if start_item.local.exists and not os.path.isdir(start_item.local_root_path):
            self._log_error('Download path must be a directory.')
            return False

        return True

    def _log_error(self, msg, error=None):
        if error:
            log_msg = '. '.join(filter(None, [msg, str(error)]))
            self.errors.append(log_msg)
            logging.exception(msg)
        else:
            self.errors.append(msg)
            logging.error(msg)

    async def _worker(self):
        while not self._abort:
            synapse_item = await self.queue.get()
            if synapse_item:
                try:
                    await synapse_item.load()

                    if self._do_compare:
                        self._add_comparable(synapse_item)

                    if synapse_item.is_folder:
                        await self._process_folder(synapse_item)
                    else:
                        await self._process_file(synapse_item)
                except Exception as ex:
                    self._log_error('Download Worker Error', error=ex)
                finally:
                    self.queue.task_done()

    async def _compare_worker(self):
        while not self._abort:
            synapse_item = await self.queue.get()
            if synapse_item:
                try:
                    await self._compare_path(synapse_item)
                except Exception as ex:
                    self._log_error('Compare Worker Error', error=ex)
                finally:
                    self.queue.task_done()

    async def _process_children(self, synapse_item):
        if self._abort:
            return
        try:
            remote_abs_base_path = await self._remote_abs_base_path(synapse_item.parent_id)
            if synapse_item.is_file:
                # Downloading or comparing a single File.
                await self.queue.put(synapse_item)
            else:
                # Downloading or comparing Projects and Folders.
                async for child in Synapsis.Chain.getChildren(synapse_item.id, includeTypes=["folder", "file"]):
                    if self._abort:
                        return
                    child_id = child.get('id')
                    child_name = child.get('name')
                    child_type = Synapsis.ConcreteTypes.get(child)
                    await self.queue.put(
                        SynapseItem(child_type,
                                    id=child_id,
                                    parent_id=synapse_item.id,
                                    name=child_name,
                                    synapse_root_path=remote_abs_base_path,
                                    local_root_path=synapse_item.local.abs_path))
        except Exception as ex:
            self._log_error('Failed to get folders and files for: {0}'.format(Synapsis.id_of(synapse_item)), error=ex)

    def can_skip(self, synapse_item):
        skip_values = [
            synapse_item.id,
            synapse_item.name,
            synapse_item.synapse_path,
            synapse_item.local.abs_path,
            synapse_item.local.name
        ]
        for skip_value in skip_values:
            if skip_value in self._excludes:
                return True

        return False

    async def _process_folder(self, synapse_folder):
        if self._abort:
            return

        full_remote_path = None
        local_abs_full_path = None
        try:
            full_remote_path = synapse_folder.synapse_path
            local_abs_full_path = synapse_folder.local.abs_path

            if self.can_skip(synapse_folder):
                logging.info('Skipping Folder: {0} ({1})'.format(full_remote_path, synapse_folder.id))
            else:
                if self._do_download:
                    if os.path.isdir(local_abs_full_path):
                        logging.info('Folder Exists: {0} -> {1}'.format(full_remote_path, local_abs_full_path))
                    else:
                        logging.info('Folder: {0} -> {1}'.format(full_remote_path, local_abs_full_path))
                        Utils.ensure_dirs(local_abs_full_path)
                else:
                    Utils.print_inplace('Folder: {0}'.format(full_remote_path))

                await self._process_children(synapse_folder)
        except Exception as ex:
            msg = 'Failed to Download:'
            if full_remote_path:
                msg += ' {0} ({1})'.format(full_remote_path, synapse_folder.id)
            else:
                msg += ' {0}'.format(synapse_folder.id)

            if local_abs_full_path:
                msg += ' -> {0}'.format(local_abs_full_path)
            self._log_error(msg, error=ex)

    async def _process_file(self, synapse_file):
        if self._abort:
            return

        full_remote_path = None
        download_path = None
        try:
            if self._do_compare and not self._do_download:
                Utils.print_inplace('File  : {0}'.format(synapse_file.synapse_path))
                return

            syn_id = synapse_file.id
            full_remote_path = synapse_file.synapse_path

            if self.can_skip(synapse_file):
                logging.info('Skipping File: {0} ({1})'.format(full_remote_path, syn_id))
            else:
                remote_md5 = synapse_file.content_md5
                content_size = synapse_file.content_size
                # NOTE: For ExternalFileHandles the size and MD5 data will not be present.
                is_unknown_size = content_size is None
                download_path = synapse_file.local.abs_path

                if download_path != Utils.real_path(download_path):
                    logging.info(
                        'Changing download path: {0} to real path: {1}'.format(download_path,
                                                                               Utils.real_path(download_path)))
                    download_path = Utils.real_path(download_path)

                local_path = os.path.dirname(download_path)
                can_download = True

                if is_unknown_size:
                    logging.info(
                        'External File: {0}, cannot determine changes. Force downloading.'.format(full_remote_path))
                elif os.path.isfile(download_path):
                    local_size = synapse_file.local.content_size
                    if local_size == content_size:
                        # Only check the md5 if the file sizes match.
                        # This way we can avoid MD5 checking for partial downloads and changed files.
                        local_md5 = await synapse_file.local.content_md5_async()
                        if local_md5 == remote_md5:
                            can_download = False
                            logging.info('File is current: {0} -> {1}'.format(full_remote_path, download_path))

                if can_download:
                    downloaded_path = None
                    if Env.SYNTOOLS_SYN_GET_DOWNLOAD():
                        downloaded_file = await Synapsis.Chain.get(syn_id,
                                                                   downloadFile=True,
                                                                   downloadLocation=local_path,
                                                                   ifcollision='overwrite.local')
                        downloaded_path = downloaded_file.path
                    else:
                        downloaded_path = await Synapsis.Chain.Synapse._downloadFileHandle(
                            synapse_file.file_handle_id,
                            syn_id,
                            'FileEntity',
                            local_path,
                            retries=Env.SYNTOOLS_DOWNLOAD_RETRIES())
                        if downloaded_path is None or downloaded_path.strip() == '':
                            raise SynToolsError('Unknown error.')

                    downloaded_real_path = Utils.real_path(downloaded_path)

                    if downloaded_real_path != download_path:
                        if os.path.exists(download_path):
                            os.remove(download_path)
                        raise SynToolsError(
                            'Downloaded path: {0} does not match expected path: {1}. Downloaded file deleted.'.format(
                                downloaded_real_path,
                                download_path))

                    downloaded_size = os.path.getsize(download_path)
                    if downloaded_size != synapse_file.content_size:
                        if os.path.exists(download_path):
                            os.remove(download_path)
                        raise FileSizeMismatchError(
                            'Downloaded size: {0} does not match expected size: {1}. Downloaded file deleted.'.format(
                                downloaded_size,
                                synapse_file.content_size))

                    logging.info('File  : {0} ({1}) -> {2} ({3})'.format(full_remote_path,
                                                                         syn_id,
                                                                         download_path,
                                                                         Utils.pretty_size(downloaded_size)))
        except Exception as ex:
            msg = 'Failed to Download:'
            if full_remote_path:
                msg += ' {0} ({1})'.format(full_remote_path, synapse_file.id)
            else:
                msg += ' {0}'.format(synapse_file.id)

            if download_path:
                msg += ' -> {0}'.format(download_path)
            else:
                msg += ' -> {0}'.format(synapse_file.local.abs_path)
            self._log_error(msg, error=ex)

    REMOTE_ABS_BASE_PATH = {}

    async def _remote_abs_base_path(self, parent_id):
        if parent_id not in self.REMOTE_ABS_BASE_PATH:
            if parent_id in self.comparables and self.comparables[parent_id]:
                path = self.comparables[parent_id][0].synapse_root_path
            else:
                try:
                    path = await Synapsis.Chain.Utils.get_synapse_path(parent_id)
                except syn.core.exceptions.SynapseHTTPError as ex:
                    if ex.response.status_code == 403:
                        # Do not have access to the parent (probably the parent of a Project).
                        path = ''

            self.REMOTE_ABS_BASE_PATH[parent_id] = path

        return self.REMOTE_ABS_BASE_PATH[parent_id]

    def _add_comparable(self, synapse_item):
        if synapse_item not in self.comparables:
            self.comparables.append(synapse_item)
        return synapse_item

    async def _compare_path(self, this_comparable):
        if self._abort:
            return
        try:
            local_items = []
            if this_comparable.is_file:
                local_dir = this_comparable.local.dirname
                if os.path.exists(local_dir):
                    local_items = list(os.scandir(local_dir))
                    local_items = Synapsis.utils.select(local_items, key='path', value=this_comparable.local.abs_path)
                comparables = [this_comparable]
            else:
                local_dir = this_comparable.local.abs_path
                if os.path.exists(local_dir):
                    local_items = list(os.scandir(local_dir))
                comparables = Synapsis.utils.select(self.comparables,
                                                    lambda c: c.local.dirname == this_comparable.local.abs_path)

            # Add missing locals.
            for local in local_items:
                if self._abort:
                    return
                local_comparable = Synapsis.utils.find(self.comparables, lambda c: c.local.abs_path == local.path)
                if not local_comparable:
                    remote_abs_base_path = await self._remote_abs_base_path(this_comparable.parent_id)
                    entity_type = Synapsis.ConcreteTypes.FOLDER_ENTITY if local.is_dir() else Synapsis.ConcreteTypes.FILE_ENTITY
                    local_comparable = SynapseItem(entity_type,
                                                   name=local.name,
                                                   parent_id=this_comparable.parent_id,
                                                   synapse_root_path=remote_abs_base_path,
                                                   local_root_path=this_comparable.local.abs_path)
                    comparables.append(local_comparable)

            comparables.sort(key=lambda c: c.synapse_path)

            # Remove any ignored files
            if self._excludes:
                for c in comparables:
                    if self.can_skip(c):
                        comparables.remove(c)
                        if c.local.exists:
                            logging.info('[SKIPPING] {0}'.format(c.local.abs_path))
                        if c.exists:
                            logging.info('[SKIPPING] {0}'.format(c.synapse_path))

            # Compare
            for c in comparables:
                if self._abort:
                    return
                if c.is_folder:
                    if c.local.exists and not c.exists:
                        self._log_error(
                            '[-] {0} <- {1} [FOLDER NOT FOUND ON SYNAPSE]'.format(c.synapse_path, c.local.abs_path))
                    elif c.exists and not c.local.exists:
                        self._log_error(
                            '[-] {0} -> {1} [FOLDER NOT FOUND LOCALLY]'.format(c.synapse_path, c.local.abs_path))
                    else:
                        logging.info('[+] {0} <-> {1}'.format(c.synapse_path, c.local.abs_path))
                        await self.queue.put(c)
                else:
                    if c.local.exists and not c.exists:
                        self._log_error(
                            '[-] {0} <- {1} [FILE NOT FOUND ON SYNAPSE]'.format(c.synapse_path, c.local.abs_path))
                    elif c.exists and not c.local.exists:
                        self._log_error(
                            '[-] {0} -> {1} [FILE NOT FOUND LOCALLY]'.format(c.synapse_path, c.local.abs_path))
                    else:
                        if c.content_size is None:
                            logging.info('[+] {0} <-> {1} [SYNAPSE FILE SIZE/MD5 UNKNOWN]'.format(
                                c.synapse_path,
                                c.local.abs_path))
                        else:
                            local_size = c.local.content_size
                            if local_size != c.content_size:
                                self._log_error('[-] {0} {1} <- {2} {3} [FILE SIZE MISMATCH]'.format(
                                    c.synapse_path,
                                    Utils.pretty_size(c.content_size),
                                    c.local.abs_path,
                                    Utils.pretty_size(local_size)))
                            else:
                                local_md5 = await c.local.content_md5_async()
                                if local_md5 != c.content_md5:
                                    self._log_error('[-] {0} {1} <- {2} {3} [FILE MD5 MISMATCH]'.format(
                                        c.synapse_path,
                                        c.content_md5,
                                        c.local.abs_path,
                                        local_md5
                                    ))
                                else:
                                    logging.info('[+] {0} <-> {1}'.format(c.synapse_path, c.local.abs_path))
        except Exception as ex:
            self._log_error(
                'Failed to Compare: {0} -> {1}'.format(this_comparable.synapse_path, this_comparable.local.abs_path),
                error=ex)
