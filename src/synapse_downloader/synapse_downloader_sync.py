import os
import getpass
import synapseclient as syn
import synapseutils
import logging
from .utils import Utils
from datetime import datetime


class SynapseDownloaderSync:
    """Use synapseutils.sync.syncFromSynapse to do recursive download.

    """

    def __init__(self, starting_entity_id, download_path, username=None, password=None):
        self._synapse_client = None
        self._starting_entity_id = starting_entity_id
        self._username = username
        self._password = password

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
        logging.info('')

        synapseutils.sync.syncFromSynapse(syn=self._synapse_client,
                                          entity=parent,
                                          path=self._download_path,
                                          ifcollision='overwrite.local')
        self.end_time = datetime.now()

        logging.info('')
        logging.info('Run time: {0}'.format(self.end_time - self.start_time))