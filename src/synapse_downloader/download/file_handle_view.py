import uuid
import logging
import synapseclient as syn
from ..core.synapse_proxy import SynapseProxy


class FileHandleView(dict):
    COL_ID = 'id'
    COL_DATAFILEHANDLEID = 'dataFileHandleId'
    COL_NAME = 'name'

    def __init__(self, scope):
        """

        Args:
            scope: The Project, Folder, or File to scope the view to.
        """
        self.scope = scope
        self.view_project = None
        self.view = None

    async def load(self):
        try:
            if isinstance(self.scope, syn.File):
                self._add_item(self.scope.id, self.scope['dataFileHandleId'], self.scope.name)
            elif type(self.scope) in [syn.Project, syn.Folder]:
                await self._create()
                logging.info('Querying file view...')
                query = await SynapseProxy.tableQueryAsync('SELECT * FROM {0}'.format(self.view.id))

                id_col = self._get_table_column_index(query.headers, self.COL_ID)
                col_datafilehandleid = self._get_table_column_index(query.headers, self.COL_DATAFILEHANDLEID)
                col_name = self._get_table_column_index(query.headers, self.COL_NAME)

                logging.info('Loading file view...')
                for row in query:
                    self._add_item(row[id_col], row[col_datafilehandleid], row[col_name])
            else:
                raise Exception('Scope entity must be a Project, Folder, or File.')
        except Exception as ex:
            logging.exception(ex)
            raise
        finally:
            await self._delete()

        return self

    async def get(self, syn_id):
        if syn_id not in self:
            entity = await SynapseProxy.getAsync(syn_id, downloadFile=False)
            self._add_item(syn_id, entity[self.COL_DATAFILEHANDLEID], entity.name)
        return self[syn_id]

    async def get_filehandle(self, syn_id):
        view_item = await self.get(syn_id)
        return await SynapseProxy.Aio.get_filehandle(syn_id, view_item.get(self.COL_DATAFILEHANDLEID))

    def _add_item(self, id, datafilehandleid, name):
        self[id] = {
            self.COL_ID: id,
            self.COL_DATAFILEHANDLEID: datafilehandleid,
            self.COL_NAME: name
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
        self.view_project = await SynapseProxy.storeAsync(syn.Project(name=name))

        logging.info('Creating file view: {0}'.format(name))
        cols = [
            syn.Column(name=self.COL_ID, columnType='ENTITYID'),
            syn.Column(name=self.COL_DATAFILEHANDLEID, columnType='FILEHANDLEID'),
            syn.Column(name=self.COL_NAME, columnType='STRING', maximumSize=256)
        ]
        schema = syn.EntityViewSchema(name=name,
                                      columns=cols,
                                      properties=None,
                                      parent=self.view_project,
                                      scopes=[self.scope],
                                      includeEntityTypes=[syn.EntityViewType.FILE],
                                      addDefaultViewColumns=False,
                                      addAnnotationColumns=False)
        self.view = await SynapseProxy.storeAsync(schema)

    async def _delete(self):
        if self.view_project:
            logging.info('Deleting file view project: {0}'.format(self.view_project.name))
            await SynapseProxy.deleteAsync(self.view_project)
