import os
import pytest
import synapseclient
from synapseclient import Project, Folder, File, Team, Wiki


def test_test_id(syn_test_helper):
    assert syn_test_helper.test_id() == syn_test_helper._test_id


def test_uniq_name(syn_test_helper):
    assert syn_test_helper.test_id() in syn_test_helper.uniq_name()

    last_name = None
    for i in list(range(3)):
        uniq_name = syn_test_helper.uniq_name(prefix='aaa-', postfix='-zzz')
        assert uniq_name != last_name
        assert uniq_name.startswith(
            'aaa-{0}'.format(syn_test_helper.test_id()))
        assert uniq_name.endswith('-zzz')
        last_name = uniq_name


def test_fake_synapse_id(syn_test_helper, syn_client):
    fake_id = syn_test_helper.fake_synapse_id()

    with pytest.raises(synapseclient.exceptions.SynapseHTTPError) as ex:
        syn_client.get(fake_id)

    err_str = str(ex.value)
    assert 'The resource you are attempting to access cannot be found' in err_str


def test_dispose_of(syn_test_helper):
    # Add a single object
    for obj in [object(), object()]:
        syn_test_helper.dispose_of(obj)
        assert obj in syn_test_helper._trash

    # Add a list of objects
    obj1 = object()
    obj2 = object()
    syn_test_helper.dispose_of(obj1, obj2)
    assert obj1 in syn_test_helper._trash
    assert obj2 in syn_test_helper._trash

    # Does not add duplicates
    syn_test_helper.dispose_of(obj1, obj2)
    assert len(syn_test_helper._trash) == 4


def test_dispose(syn_client, syn_test_helper, mk_tempfile):
    project = syn_client.store(Project(name=syn_test_helper.uniq_name()))

    folder = syn_client.store(
        Folder(name=syn_test_helper.uniq_name(prefix='Folder '), parent=project))

    file = syn_client.store(File(name=syn_test_helper.uniq_name(
        prefix='File '), path=mk_tempfile(), parent=folder))

    team = syn_client.store(
        Team(name=syn_test_helper.uniq_name(prefix='Team ')))

    wiki = syn_client.store(
        Wiki(title=syn_test_helper.uniq_name(prefix='Wiki '), owner=project))

    wikiChild = syn_client.store(Wiki(title=syn_test_helper.uniq_name(
        prefix='Wiki Child '), owner=project, parentWikiId=wiki.id))

    syn_objects = [project, folder, file, team, wiki, wikiChild]

    for syn_obj in syn_objects:
        syn_test_helper.dispose_of(syn_obj)
        assert syn_obj in syn_test_helper._trash

    syn_test_helper.dispose()
    assert len(syn_test_helper._trash) == 0

    for syn_obj in syn_objects:
        with pytest.raises(synapseclient.exceptions.SynapseHTTPError) as ex:
            if isinstance(syn_obj, Wiki):
                syn_client.getWiki(syn_obj)
            elif isinstance(syn_obj, Team):
                syn_client.getTeam(syn_obj.id)
            else:
                syn_client.get(syn_obj, downloadFile=False)

        err_str = str(ex.value)
        assert "Not Found" in err_str or "cannot be found" in err_str or "is in trash can" in err_str or "does not exist" in err_str


def test_create_project(syn_test_helper):
    # Uses the name arg
    name = syn_test_helper.uniq_name()
    project = syn_test_helper.create_project(name=name)
    assert project.name == name
    assert project in syn_test_helper._trash
    syn_test_helper.dispose()
    assert project not in syn_test_helper._trash

    # Uses the prefix arg
    prefix = '-z-z-z-'
    project = syn_test_helper.create_project(prefix=prefix)
    assert project.name.startswith(prefix)

    # Generates a name
    project = syn_test_helper.create_project()
    assert syn_test_helper.test_id() in project.name


def test_create_team(syn_test_helper):
    # Uses the name arg
    name = syn_test_helper.uniq_name()
    team = syn_test_helper.create_team(name=name)
    assert team.name == name
    assert team in syn_test_helper._trash
    syn_test_helper.dispose()
    assert team not in syn_test_helper._trash

    # Uses the prefix arg
    prefix = '-z-z-z-'
    team = syn_test_helper.create_team(prefix=prefix)
    assert team.name.startswith(prefix)

    # Generates a name
    team = syn_test_helper.create_team()
    assert syn_test_helper.test_id() in team.name


def test_create_wiki(syn_test_helper):
    project = syn_test_helper.create_project()

    # Uses the title arg
    title = syn_test_helper.uniq_name()
    wiki = syn_test_helper.create_wiki(title=title, owner=project)
    assert wiki.title == title
    assert wiki in syn_test_helper._trash

    # Uses the prefix arg
    prefix = '-z-z-z-'
    wiki = syn_test_helper.create_wiki(prefix=prefix, owner=project)
    assert wiki.title.startswith(prefix)

    # Generates a title
    wiki = syn_test_helper.create_wiki(owner=project)
    assert syn_test_helper.test_id() in wiki.title

    syn_test_helper.dispose()
    assert len(syn_test_helper._trash) == 0
