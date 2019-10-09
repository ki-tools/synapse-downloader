import os
import synapseclient as syn
import logging
from datetime import datetime
from .utils import Utils
from .synapse_proxy import SynapseProxy


class SynapseDownloaderOld:
    def __init__(self, starting_entity_id, download_path, username=None, password=None):
        self._starting_entity_id = starting_entity_id
        self._username = username
        self._password = password

        self.start_time = None
        self.end_time = None

        var_path = os.path.expandvars(download_path)
        expanded_path = os.path.expanduser(var_path)
        self._download_path = expanded_path

    def start(self):
        self.start_time = datetime.now()

        Utils.ensure_dirs(self._download_path)

        SynapseProxy.login(username=self._username, password=self._password)
        parent = SynapseProxy.get(self._starting_entity_id, downloadFile=False)
        if type(parent) not in [syn.Project, syn.Folder]:
            raise Exception('Starting entity must be a Project or Folder.')
        logging.info('Starting entity: {0} ({1})'.format(parent.name, parent.id))
        logging.info('Downloading to: {0}'.format(self._download_path))
        logging.info('')

        self.start_time = datetime.now()
        self.download_children(parent, self._download_path)

        self.end_time = datetime.now()
        logging.info('')
        logging.info('Run time: {0}'.format(self.end_time - self.start_time))

    def download_children(self, parent, local_path):
        syn_folders = []
        syn_files = []

        try:
            children = SynapseProxy.getChildren(parent, includeTypes=["folder", "file"])

            for child in children:
                child_id = child.get('id')
                child_name = child.get('name')

                if child.get('type') == 'org.sagebionetworks.repo.model.Folder':
                    syn_folders.append({'id': child_id, 'name': child_name, 'local_path': local_path})
                else:
                    syn_files.append({'id': child_id, 'name': child_name, 'local_path': local_path})

            if syn_files:
                for syn_file in syn_files:
                    self.download_file(syn_file['id'], syn_file['name'], syn_file['local_path'])

            if syn_folders:
                for syn_folder in syn_folders:
                    self.download_folder(syn_folder['id'], syn_folder['name'], syn_folder['local_path'])

        except Exception as ex:
            logging.exception(ex)

    def download_folder(self, syn_id, name, local_path):
        try:
            full_path = os.path.join(local_path, name)
            logging.info('Folder: {0} -> {1}'.format(syn_id, full_path))
            Utils.ensure_dirs(full_path)
            self.download_children(syn_id, full_path)
        except Exception as ex:
            logging.exception(ex)

    def download_file(self, syn_id, name, local_path):
        try:
            full_path = os.path.join(local_path, name)
            logging.info('File  : {0} -> {1}'.format(syn_id, full_path))
            SynapseProxy.get(syn_id,
                             downloadFile=True,
                             downloadLocation=local_path,
                             ifcollision='overwrite.local')
        except Exception as ex:
            logging.exception(ex)
