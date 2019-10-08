import os
import logging
import getpass
import asyncio
import synapseclient as syn
from functools import partial


class SynapseProxy:
    _synapse_client = None

    @classmethod
    def login(cls, username=None, password=None):
        username = username or os.getenv('SYNAPSE_USERNAME')
        password = password or os.getenv('SYNAPSE_PASSWORD')

        if not username:
            username = input('Synapse username: ')

        if not password:
            password = getpass.getpass(prompt='Synapse password: ')

        logging.info('Logging into Synapse as: {0}'.format(username))
        try:
            # Disable the synapseclient progress output.
            syn.utils.printTransferProgress = lambda *a, **k: None

            cls._synapse_client = syn.Synapse(skip_checks=True)
            cls._synapse_client.login(username, password, silent=True)
        except Exception as ex:
            cls._synapse_client = None
            logging.error('Synapse login failed: {0}'.format(str(ex)))

        return cls._synapse_client is not None

    @classmethod
    def client(cls):
        if not cls._synapse_client:
            cls.login()
        return cls._synapse_client

    @classmethod
    def store(cls, obj, **kwargs):
        return cls.client().store(obj, **kwargs)

    @classmethod
    async def storeAsync(cls, obj, **kwargs):
        args = partial(cls.store, obj=obj, **kwargs)
        return await asyncio.get_running_loop().run_in_executor(None, args)

    @classmethod
    def get(cls, entity, **kwargs):
        return cls.client().get(entity, **kwargs)

    @classmethod
    async def getAsync(cls, entity, **kwargs):
        args = partial(cls.get, entity=entity, **kwargs)
        return await asyncio.get_running_loop().run_in_executor(None, args)

    @classmethod
    def getChildren(cls, parent, **kwargs):
        return list(cls.client().getChildren(parent, **kwargs))

    @classmethod
    async def getChildrenAsync(cls, parent, **kwargs):
        args = partial(cls.getChildren, parent=parent, **kwargs)
        return await asyncio.get_running_loop().run_in_executor(None, args)

    @classmethod
    def tableQuery(cls, query, resultsAs="csv", **kwargs):
        return cls.client().tableQuery(query=query, resultsAs=resultsAs, **kwargs)

    @classmethod
    async def tableQueryAsync(cls, query, resultsAs="csv", **kwargs):
        args = partial(cls.tableQuery, query=query, resultsAs=resultsAs, **kwargs)
        return await asyncio.get_running_loop().run_in_executor(None, args)

    @classmethod
    def delete(cls, obj, version=None):
        return cls.client().delete(obj, version=version)

    @classmethod
    async def deleteAsync(cls, obj, version=None):
        args = partial(cls.delete, obj=obj, version=version)
        return await asyncio.get_running_loop().run_in_executor(None, args)
