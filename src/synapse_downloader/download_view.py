import uuid
import logging
from .synapse_proxy import SynapseProxy
import synapseclient as syn
from .utils import Utils


class DownloadView(dict):
    VIEW_NAME = '_temp_{0}_synapse_downloader_'.format(str(uuid.uuid4()))
    COL_ID = 'id'
    COL_DATAFILEHANDLEID = 'dataFileHandleId'

    def __init__(self, scope, aiosession):
        """

        Args:
            scope: The Project or Folder to scope the view to.
        """
        self.scope = scope
        self._aiosession = aiosession
        self.project = None
        self.view = None

    async def load(self):
        try:
            await self._create()
            logging.info('Querying file view...')
            query = await SynapseProxy.tableQueryAsync('SELECT * FROM {0}'.format(self.view.id))

            id_col = self._get_table_column_index(query.headers, self.COL_ID)
            col_datafilehandleid = self._get_table_column_index(query.headers, self.COL_DATAFILEHANDLEID)

            logging.info('Loading file view...')
            for row in query:
                self._add_item(row[id_col], row[col_datafilehandleid])
        except Exception as ex:
            logging.exception(ex)
            raise
        finally:
            await self._delete()

        return self

    async def get(self, syn_id):
        if syn_id not in self:
            self._add_item(syn_id, await self._get_file_handle_id(syn_id))
        return self[syn_id]

    async def _get_file_handle_id(self, syn_id):
        request = {
            'includeEntity': True,
            'includeAnnotations': False,
            'includePermissions': False,
            'includeEntityPath': False,
            'includeHasChildren': False,
            'includeAccessControlList': False,
            'includeFileHandles': False,
            'includeTableBundle': False,
            'includeRootWikiId': False,
            'includeBenefactorACL': False,
            'includeDOIAssociation': False,
            'includeFileName': False,
            'includeThreadCount': False,
            'includeRestrictionInformation': False
        }

        res = await Utils.rest_post(self._aiosession, '/entity/{0}/bundle2'.format(syn_id), body=request)

        return res.get('entity').get('dataFileHandleId')

    def _add_item(self, id, datafilehandleid):
        self[id] = {
            self.COL_ID: id,
            self.COL_DATAFILEHANDLEID: datafilehandleid
        }

    def _get_table_column_index(self, headers, column_name):
        """Gets the column index for a Synapse Table Column.
        """
        for index, item in enumerate(headers):
            if item.name == column_name:
                return index

    async def _create(self):
        name = '_TEMP_{0}_TEMP_'.format(str(uuid.uuid4()))
        logging.info('Creating file view project: {0}'.format(name))
        self.project = await SynapseProxy.storeAsync(syn.Project(name=name))

        logging.info('Creating file view: {0}'.format(name))
        cols = [
            syn.Column(name=self.COL_ID, columnType='ENTITYID'),
            syn.Column(name=self.COL_DATAFILEHANDLEID, columnType='FILEHANDLEID')
        ]
        schema = syn.EntityViewSchema(name=self.VIEW_NAME,
                                      columns=cols,
                                      properties=None,
                                      parent=self.project,
                                      scopes=[self.scope],
                                      includeEntityTypes=[syn.EntityViewType.FILE],
                                      addDefaultViewColumns=False,
                                      addAnnotationColumns=False)
        self.view = await SynapseProxy.storeAsync(schema)

    async def _delete(self):
        if self.project:
            logging.info('Deleting file view project: {0}'.format(self.project.name))
            await SynapseProxy.deleteAsync(self.project)
