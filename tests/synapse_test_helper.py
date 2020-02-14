import uuid
from src.synapse_downloader.core import SynapseProxy
from synapseclient import Project, Folder, File, Team, Wiki


class SynapseTestHelper:
    """Test helper for working with Synapse."""

    _test_id = uuid.uuid4().hex
    _trash = []

    def test_id(self):
        """Gets a unique value to use as a test identifier.

        This string can be used to help identify the test instance that created the object.
        """
        return self._test_id

    def uniq_name(self, prefix='', postfix=''):
        return "{0}{1}_{2}{3}".format(prefix, self.test_id(), uuid.uuid4().hex, postfix)

    def fake_synapse_id(self):
        """Gets a Synapse entity ID that does not exist in Synapse.

        Returns:
            String
        """
        return 'syn000'

    def dispose_of(self, *syn_objects):
        """Adds a Synapse object to the list of objects to be deleted."""
        for syn_object in syn_objects:
            if syn_object not in self._trash:
                self._trash.append(syn_object)

    def dispose(self):
        """Cleans up any Synapse objects that were created during testing.

        This method needs to be manually called after each or all tests are done.
        """
        projects = []
        folders = []
        files = []
        teams = []
        wikis = []
        others = []

        for obj in self._trash:
            if isinstance(obj, Project):
                projects.append(obj)
            elif isinstance(obj, Folder):
                folders.append(obj)
            elif isinstance(obj, File):
                files.append(obj)
            elif isinstance(obj, Team):
                teams.append(obj)
            elif isinstance(obj, Wiki):
                wikis.append(obj)
            else:
                others.append(obj)

        for syn_obj in wikis:
            try:
                SynapseProxy.client().delete(syn_obj)
            except:
                pass
            self._trash.remove(syn_obj)

        for syn_obj in files:
            try:
                SynapseProxy.client().delete(syn_obj)
            except:
                pass
            self._trash.remove(syn_obj)

        for syn_obj in folders:
            try:
                SynapseProxy.client().delete(syn_obj)
            except:
                pass
            self._trash.remove(syn_obj)

        for syn_obj in projects:
            try:
                SynapseProxy.client().delete(syn_obj)
            except:
                pass
            self._trash.remove(syn_obj)

        for syn_obj in teams:
            try:
                SynapseProxy.client().delete(syn_obj)
            except:
                pass
            self._trash.remove(syn_obj)

        for obj in others:
            print('WARNING: Non-Supported object found: {0}'.format(obj))
            self._trash.remove(obj)

    def create_project(self, **kwargs):
        """Creates a new Project and adds it to the trash queue."""
        if 'name' not in kwargs:
            kwargs['name'] = self.uniq_name(prefix=kwargs.get('prefix', ''))

        kwargs.pop('prefix', None)

        project = SynapseProxy.client().store(Project(**kwargs))
        self.dispose_of(project)
        return project

    def create_folder(self, **kwargs):
        """Creates a new Folder and adds it to the trash queue."""
        if 'name' not in kwargs:
            kwargs['name'] = self.uniq_name(prefix=kwargs.get('prefix', ''))

        kwargs.pop('prefix', None)

        folder = SynapseProxy.client().store(Folder(**kwargs))
        self.dispose_of(folder)
        return folder

    def create_file(self, **kwargs):
        """Creates a new File and adds it to the trash queue."""
        if 'name' not in kwargs:
            kwargs['name'] = self.uniq_name(prefix=kwargs.get('prefix', ''))

        kwargs.pop('prefix', None)

        file = SynapseProxy.client().store(File(**kwargs))
        self.dispose_of(file)
        return file

    def create_team(self, **kwargs):
        """Creates a new Team and adds it to the trash queue."""
        if 'name' not in kwargs:
            kwargs['name'] = self.uniq_name(prefix=kwargs.get('prefix', ''))

        kwargs.pop('prefix', None)

        team = SynapseProxy.client().store(Team(**kwargs))
        self.dispose_of(team)
        return team

    def create_wiki(self, **kwargs):
        """Creates a new Wiki and adds it to the trash queue."""
        if 'title' not in kwargs:
            kwargs['title'] = self.uniq_name(prefix=kwargs.get('prefix', ''))
        kwargs.pop('prefix', None)

        if 'markdown' not in kwargs:
            kwargs['markdown'] = 'My Wiki {0}'.format(kwargs['title'])

        wiki = SynapseProxy.client().store(Wiki(**kwargs))
        self.dispose_of(wiki)
        return wiki
