import uuid
import logging
import synapseclient as syn


class DownloadFileView(dict):
    VIEW_NAME = '_temp_{0}_synapse_downloader_'.format(str(uuid.uuid4()))
    COL_ID = 'id'
    COL_PARENTID = 'parentId'
    COL_DATAFILEHANDLEID = 'dataFileHandleId'

    def __init__(self, syn_client, project):
        self.syn_client = syn_client
        self.project = project
        self.view = None

    def load(self):
        try:
            self._ensure_view()
            logging.info('Querying file view...')
            query = self.syn_client.tableQuery('SELECT * FROM {0}'.format(self.view.id))

            id_col = self._get_table_column_index(query.headers, self.COL_ID)
            col_parentid = self._get_table_column_index(query.headers, self.COL_PARENTID)
            col_datafilehandleid = self._get_table_column_index(query.headers, self.COL_DATAFILEHANDLEID)

            logging.info('Loading file view...')
            for row in query:
                self[row[id_col]] = {
                    self.COL_ID: row[id_col],
                    self.COL_PARENTID: row[col_parentid],
                    self.COL_DATAFILEHANDLEID: row[col_datafilehandleid]
                }
        except Exception as ex:
            logging.exception(ex)
            raise
        finally:
            self.delete()

        return self

    def _get_table_column_index(self, headers, column_name):
        """Gets the column index for a Synapse Table Column.
        """
        for index, item in enumerate(headers):
            if item.name == column_name:
                return index

    def _ensure_view(self):
        logging.info('Creating file view: {0}'.format(self.VIEW_NAME))
        cols = [
            syn.Column(name=self.COL_ID, columnType='ENTITYID'),
            syn.Column(name=self.COL_PARENTID, columnType='ENTITYID'),
            syn.Column(name=self.COL_DATAFILEHANDLEID, columnType='FILEHANDLEID')
        ]
        schema = syn.EntityViewSchema(name=self.VIEW_NAME,
                                      columns=cols,
                                      properties=None,
                                      parent=self.project,
                                      scopes=[self.project],
                                      includeEntityTypes=[syn.EntityViewType.FILE],
                                      addDefaultViewColumns=False,
                                      addAnnotationColumns=False)
        self.view = self.syn_client.store(schema)

    def delete(self):
        if self.view:
            logging.info('Deleting file view: {0}'.format(self.VIEW_NAME))
            self.syn_client.delete(self.view)
