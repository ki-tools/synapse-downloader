import os
import synapseclient as syn
import synapseutils
import logging
from .utils import Utils
from datetime import datetime
from .synapse_proxy import SynapseProxy


class SynapseDownloaderSync:
    """Use synapseutils.sync.syncFromSynapse to do recursive download.

    """

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
        Utils.ensure_dirs(self._download_path)

        SynapseProxy.login(username=self._username, password=self._password)
        parent = SynapseProxy.get(self._starting_entity_id, downloadFile=False)
        if type(parent) not in [syn.Project, syn.Folder]:
            raise Exception('Starting entity must be a Project or Folder.')
        logging.info('Starting entity: {0} ({1})'.format(parent.name, parent.id))
        logging.info('Downloading to: {0}'.format(self._download_path))
        logging.info('')

        self.start_time = datetime.now()
        synapseutils.sync.syncFromSynapse(syn=SynapseProxy.client(),
                                          entity=parent,
                                          path=self._download_path,
                                          ifcollision='overwrite.local')
        self.end_time = datetime.now()

        logging.info('')
        logging.info('Run time: {0}'.format(self.end_time - self.start_time))
