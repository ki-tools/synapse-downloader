import pytest
import os
import shutil
from src.synapse_downloader.download.downloader import Downloader
import synapseclient as syn


@pytest.fixture(scope='module')
def syn_data(syn_test_helper_class, mk_tempdir, mk_tempfile):
    download_dir = mk_tempdir()

    project = syn_test_helper_class.create_project(prefix='Project-')
    file0 = mk_tempfile()
    syn_file0 = syn_test_helper_class.create_file(prefix='file0-', path=file0, parent=project)

    syn_folder1 = syn_test_helper_class.create_folder(prefix='folder1-', parent=project)
    file1 = mk_tempfile()
    syn_file1 = syn_test_helper_class.create_file(prefix='file1-', path=file1, parent=syn_folder1)

    syn_folder2 = syn_test_helper_class.create_folder(prefix='folder2-', parent=syn_folder1)
    file2 = mk_tempfile()
    syn_file2 = syn_test_helper_class.create_file(prefix='file2-', path=file2, parent=syn_folder2)

    syn_file0_download_path = os.path.join(download_dir, syn_file0._file_handle.fileName)
    syn_folder1_download_path = os.path.join(download_dir, syn_folder1.name)
    syn_file1_download_path = os.path.join(syn_folder1_download_path, syn_file1._file_handle.fileName)
    syn_folder2_download_path = os.path.join(syn_folder1_download_path, syn_folder2.name)
    syn_file2_download_path = os.path.join(syn_folder2_download_path, syn_file2._file_handle.fileName)

    result = {
        'download_dir': download_dir,
        'project': project,
        'file0': file0,
        'syn_file0': syn_file0,
        'syn_file0_download_path': syn_file0_download_path,
        'syn_folder1': syn_folder1,
        'syn_folder1_download_path': syn_folder1_download_path,
        'file1': file1,
        'syn_file1': syn_file1,
        'syn_file1_download_path': syn_file1_download_path,
        'syn_folder2': syn_folder2,
        'syn_folder2_download_path': syn_folder2_download_path,
        'file2': file2,
        'syn_file2': syn_file2,
        'syn_file2_download_path': syn_file2_download_path,
        'all_syn_entities': [syn_folder1, syn_folder2, syn_file0, syn_file1, syn_file2],
        'all_syn_folders': [syn_folder1, syn_folder2],
        'all_syn_files': [syn_file0, syn_file1, syn_file2]
    }

    result['{0}_download_path'.format(syn_folder1.name)] = syn_folder1_download_path
    result['{0}_download_path'.format(syn_folder2.name)] = syn_folder2_download_path

    result['{0}_download_path'.format(syn_file0._file_handle.fileName)] = syn_file0_download_path
    result['{0}_download_path'.format(syn_file1._file_handle.fileName)] = syn_file1_download_path
    result['{0}_download_path'.format(syn_file2._file_handle.fileName)] = syn_file2_download_path

    return result


@pytest.fixture
def reset_download_dir():
    def _reset(syn_data):
        download_dir = syn_data['download_dir']
        if os.path.exists(download_dir):
            shutil.rmtree(download_dir)

    yield _reset


def assert_local_download_data(syn_data, expect=[], not_expect=[]):
    if not expect and not not_expect:
        raise Exception('must specify one: expect or not_expect')

    for syn_entity in expect:
        if isinstance(syn_entity, syn.File):
            assert os.path.isfile(syn_data.get('{0}_download_path'.format(syn_entity._file_handle.fileName)))
        else:
            assert os.path.isdir(syn_data.get('{0}_download_path'.format(syn_entity.name)))

    for syn_entity in not_expect:
        if isinstance(syn_entity, syn.File):
            assert not os.path.isfile(syn_data.get('{0}_download_path'.format(syn_entity._file_handle.fileName)))
        else:
            assert not os.path.isdir(syn_data.get('{0}_download_path'.format(syn_entity.name)))


def test_it_downloads_everything(syn_data, reset_download_dir):
    reset_download_dir(syn_data)
    download_dir = syn_data['download_dir']
    project = syn_data['project']
    all_syn_entities = syn_data['all_syn_entities']

    downloader = Downloader(project.id, download_dir)
    downloader.start()
    assert len(downloader.errors) == 0
    assert_local_download_data(syn_data, expect=all_syn_entities)


def test_it_downloads_everything_with_entity_view(syn_data, reset_download_dir):
    reset_download_dir(syn_data)
    download_dir = syn_data['download_dir']
    project = syn_data['project']
    all_syn_entities = syn_data['all_syn_entities']

    downloader = Downloader(project.id, download_dir, with_view=True)
    downloader.start()
    assert len(downloader.errors) == 0
    # TODO: Figure out how to test the view was used.
    assert_local_download_data(syn_data, expect=all_syn_entities)


def test_it_excludes_folders_by_id(syn_data, reset_download_dir):
    download_dir = syn_data['download_dir']
    project = syn_data['project']
    syn_file0 = syn_data['syn_file0']
    syn_folder1 = syn_data['syn_folder1']
    syn_file1 = syn_data['syn_file1']
    syn_folder2 = syn_data['syn_folder2']
    syn_file2 = syn_data['syn_file2']

    for with_view in [False, True]:
        reset_download_dir(syn_data)
        downloader = Downloader(project.id, download_dir, with_view=with_view, excludes=[syn_folder1.id])
        downloader.start()
        assert len(downloader.errors) == 0
        assert_local_download_data(syn_data,
                                   expect=[syn_file0],
                                   not_expect=[syn_folder1, syn_file1, syn_folder2, syn_file2])

        reset_download_dir(syn_data)
        downloader = Downloader(project.id, download_dir, with_view=with_view, excludes=[syn_folder2.id])
        downloader.start()
        assert len(downloader.errors) == 0
        assert_local_download_data(syn_data,
                                   expect=[syn_file0, syn_folder1, syn_file1],
                                   not_expect=[syn_folder2, syn_file2])


def test_it_excludes_folders_by_name(syn_data, reset_download_dir):
    download_dir = syn_data['download_dir']
    project = syn_data['project']
    syn_file0 = syn_data['syn_file0']
    syn_folder1 = syn_data['syn_folder1']
    syn_file1 = syn_data['syn_file1']
    syn_folder2 = syn_data['syn_folder2']
    syn_file2 = syn_data['syn_file2']

    for with_view in [False, True]:
        reset_download_dir(syn_data)
        downloader = Downloader(project.id, download_dir, with_view=with_view, excludes=[syn_folder1.name])
        downloader.start()
        assert len(downloader.errors) == 0
        assert_local_download_data(syn_data,
                                   expect=[syn_file0],
                                   not_expect=[syn_folder1, syn_file1, syn_folder2, syn_file2])

        reset_download_dir(syn_data)
        downloader = Downloader(project.id, download_dir, with_view=with_view, excludes=[syn_folder2.name])
        downloader.start()
        assert len(downloader.errors) == 0
        assert_local_download_data(syn_data,
                                   expect=[syn_file0, syn_folder1, syn_file1],
                                   not_expect=[syn_folder2, syn_file2])


def test_it_excludes_files_by_id(syn_data, reset_download_dir):
    download_dir = syn_data['download_dir']
    project = syn_data['project']
    all_syn_entities = syn_data['all_syn_entities']
    all_syn_folders = syn_data['all_syn_folders']
    all_syn_files = syn_data['all_syn_files']

    for with_view in [False, True]:
        # Exclude each file
        for syn_file in all_syn_files:
            reset_download_dir(syn_data)
            downloader = Downloader(project.id, download_dir, with_view=with_view, excludes=[syn_file.id])
            downloader.start()
            expected = all_syn_entities.copy()
            expected.remove(syn_file)
            assert len(downloader.errors) == 0
            assert_local_download_data(syn_data,
                                       expect=expected,
                                       not_expect=[syn_file])

        # Exclude all files
        reset_download_dir(syn_data)
        downloader = Downloader(project.id, download_dir, with_view=with_view, excludes=[f.id for f in all_syn_files])
        downloader.start()
        assert len(downloader.errors) == 0
        assert_local_download_data(syn_data,
                                   expect=all_syn_folders,
                                   not_expect=all_syn_files)


def test_it_excludes_files_by_name(syn_data, reset_download_dir):
    download_dir = syn_data['download_dir']
    project = syn_data['project']
    all_syn_entities = syn_data['all_syn_entities']
    all_syn_folders = syn_data['all_syn_folders']
    all_syn_files = syn_data['all_syn_files']

    for with_view in [False, True]:
        # Exclude each file
        for syn_file in all_syn_files:
            reset_download_dir(syn_data)
            downloader = Downloader(project.id, download_dir, with_view=with_view, excludes=[syn_file.name])
            downloader.start()
            expected = all_syn_entities.copy()
            expected.remove(syn_file)
            assert len(downloader.errors) == 0
            assert_local_download_data(syn_data,
                                       expect=expected,
                                       not_expect=[syn_file])

        # Exclude all files
        reset_download_dir(syn_data)
        downloader = Downloader(project.id, download_dir, with_view=with_view, excludes=[f.name for f in all_syn_files])
        downloader.start()
        assert len(downloader.errors) == 0
        assert_local_download_data(syn_data,
                                   expect=all_syn_folders,
                                   not_expect=all_syn_files)


def test_it_excludes_files_by_filename(syn_data, reset_download_dir):
    download_dir = syn_data['download_dir']
    project = syn_data['project']
    all_syn_entities = syn_data['all_syn_entities']
    all_syn_folders = syn_data['all_syn_folders']
    all_syn_files = syn_data['all_syn_files']

    for with_view in [False, True]:
        # Exclude each file
        for syn_file in all_syn_files:
            reset_download_dir(syn_data)
            downloader = Downloader(project.id, download_dir, with_view=with_view,
                                    excludes=[syn_file._file_handle.fileName])
            downloader.start()
            expected = all_syn_entities.copy()
            expected.remove(syn_file)
            assert len(downloader.errors) == 0
            assert_local_download_data(syn_data,
                                       expect=expected,
                                       not_expect=[syn_file])

        # Exclude all files
        reset_download_dir(syn_data)
        downloader = Downloader(project.id, download_dir, with_view=with_view,
                                excludes=[f._file_handle.fileName for f in all_syn_files])
        downloader.start()
        assert len(downloader.errors) == 0
        assert_local_download_data(syn_data,
                                   expect=all_syn_folders,
                                   not_expect=all_syn_files)

# TODO: test downloading files of: 'concreteType': 'org.sagebionetworks.repo.model.file.ExternalFileHandle'

# TODO: Add additional tests...
