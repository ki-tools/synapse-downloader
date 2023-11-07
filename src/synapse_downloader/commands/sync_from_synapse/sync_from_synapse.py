import logging
from datetime import datetime
from synapse_downloader.core import Utils
from synapsis import Synapsis


class SyncFromSynapse:
    def __init__(self, starting_entity_id, download_path):
        self._starting_entity_id = starting_entity_id
        self._download_path = Utils.expand_path(download_path)
        self.start_time = None
        self.end_time = None
        self.errors = []

    def abort(self):
        self._log_error('User Aborted.')

    async def execute(self):
        self.start_time = datetime.now()
        self.errors = []

        start_entity = await Synapsis.Chain.get(self._starting_entity_id, downloadFile=False)
        logging.info('Syncing: {0} ({1}) to {2}'.format(start_entity.name, start_entity.id, self._download_path))

        downloaded = Synapsis.SynapseUtils.syncFromSynapse(self._starting_entity_id,
                                                           path=self._download_path,
                                                           downloadFile=True)
        for entity in downloaded:
            label = Synapsis.ConcreteTypes.get(entity).name
            logging.info('{0}: {1} -> {2}'.format(label, entity.properties['name'], entity.path))

        self.end_time = datetime.now()
        logging.info('')
        logging.info('Run time: {0}'.format(self.end_time - (self.start_time or datetime.now())))
        return self

    def _log_error(self, msg):
        if isinstance(msg, Exception):
            self.errors.append(str(msg))
            logging.exception(msg)
        else:
            self.errors.append(msg)
            logging.error(msg)
