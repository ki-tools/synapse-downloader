import os
from synapsis import Synapsis
import synapseclient as syn


class SynapseItem:

    def __init__(self,
                 type,
                 id=None,
                 parent_id=None,
                 name=None,
                 local_root_path=None,
                 synapse_root_path=None):

        self.type = type if isinstance(type, Synapsis.ConcreteTypes) else None
        self.id = id
        self.parent_id = parent_id
        self.name = name
        self.local_root_path = local_root_path
        self.synapse_root_path = synapse_root_path
        self.file_handle_id = None
        self.filename = None
        self.content_size = None
        self.content_md5 = None

        if isinstance(type, syn.Entity):
            entity = type
            self.type = Synapsis.ConcreteTypes.get(type)
            if self.id is None:
                self.id = entity.id
            if self.parent_id is None:
                self.parent_id = entity.id if self.type.is_project else entity.parentId
            if self.name is None:
                self.name = entity.name

            if isinstance(entity, syn.File):
                self.set_file_handle(entity.get('_file_handle'))

        assert isinstance(self.type, Synapsis.ConcreteTypes)
        if self.is_project:
            assert self.parent_id == self.id or self.parent_id is None
        else:
            assert self.parent_id is not None
        assert self.name is not None
        assert self.local_root_path is not None
        assert self.synapse_root_path is not None

        self.local = self.Local(self)

    @property
    def exists(self):
        return self.id is not None

    @property
    def is_project(self):
        return self.type.is_project

    @property
    def is_folder(self):
        return self.type.is_folder

    @property
    def is_file(self):
        return self.type.is_file

    @property
    def synapse_path(self):
        name = self.name
        if self.is_file and self.filename:
            name = self.filename

        segments = [s for s in [self.synapse_root_path, name] if s]
        return '/'.join(segments)

    @property
    def is_loaded(self):
        if self.is_file and (self.file_handle_id is None or self.filename is None):
            return False

        return True

    async def load(self):
        if not self.is_loaded and self.id is not None:
            if self.is_file:
                filehandle = await Synapsis.Chain.Utils.get_filehandle(self.id)
                self.set_file_handle(filehandle)

        return self

    def set_file_handle(self, file_handle):
        if not self.is_file:
            raise Exception('File Handle can only be set on files.')
        filehandle = file_handle.get('fileHandle', None) or file_handle
        self.file_handle_id = filehandle.get('id')
        self.filename = filehandle.get('fileName')
        self.content_md5 = filehandle.get('contentMd5')
        self.content_size = filehandle.get('contentSize')

    class Local:
        def __init__(self, synapse_item):
            self.synapse_item = synapse_item

        @property
        def exists(self):
            return os.path.exists(self.abs_path)

        @property
        def is_dir(self):
            return os.path.isdir(self.abs_path)

        @property
        def is_file(self):
            return os.path.isfile(self.abs_path)

        @property
        def abs_path(self):
            if self.synapse_item.is_project:
                return os.path.abspath(self.synapse_item.local_root_path)

            name = self.synapse_item.name

            if self.synapse_item.is_file and self.synapse_item.filename is not None:
                name = self.synapse_item.filename

            if name is not None:
                return os.path.abspath(os.path.join(self.synapse_item.local_root_path, name))

            return None

        @property
        def dirname(self):
            return os.path.dirname(self.abs_path)

        @property
        def name(self):
            return os.path.basename(self.abs_path)

        @property
        def content_size(self):
            if self.is_file:
                return os.path.getsize(self.abs_path)
            return None

        @property
        def content_md5(self):
            if self.is_file:
                return Synapsis.Utils.md5sum(self.abs_path)
            return None

        async def content_md5_async(self):
            if self.is_file:
                return await Synapsis.Chain.Utils.md5sum(self.abs_path)
            return None
