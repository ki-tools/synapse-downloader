import pytest
import shutil
import os
from synapse_downloader.core import Env
from synapse_downloader.commands.download.downloader import Downloader


@pytest.fixture(autouse=True)
def before_each(syn_data, reset_download_dir):
    reset_download_dir(syn_data)


@pytest.fixture()
def mock_SYNTOOLS_SYN_GET_DOWNLOAD(monkeypatch):
    def _m(value):
        monkeypatch.setenv('SYNTOOLS_SYN_GET_DOWNLOAD', str(value).lower())
        Env._SYNTOOLS_SYN_GET_DOWNLOAD = None
        assert Env.SYNTOOLS_SYN_GET_DOWNLOAD() == value

    yield _m


async def test_it_downloads_everything(syn_data, assert_local_download_data, reset_download_dir,
                                       mock_SYNTOOLS_SYN_GET_DOWNLOAD):
    for syntools_syn_get_download in [True, False]:
        mock_SYNTOOLS_SYN_GET_DOWNLOAD(syntools_syn_get_download)
        reset_download_dir(syn_data)
        download_dir = syn_data['download_dir']
        project = syn_data['project']
        all_syn_entities = syn_data['all_syn_entities']

        downloader = Downloader(project.id, download_dir)
        await downloader.execute()
        assert len(downloader.errors) == 0
        assert_local_download_data(syn_data, expect=all_syn_entities)


async def test_it_downloads_and_compares_everything(syn_data, assert_local_download_data, reset_download_dir,
                                                    mock_SYNTOOLS_SYN_GET_DOWNLOAD):
    for syntools_syn_get_download in [True, False]:
        mock_SYNTOOLS_SYN_GET_DOWNLOAD(syntools_syn_get_download)
        reset_download_dir(syn_data)
        download_dir = syn_data['download_dir']
        project = syn_data['project']
        all_syn_entities = syn_data['all_syn_entities']

        downloader = Downloader(project.id, download_dir, download=True, compare=True)
        await downloader.execute()
        assert len(downloader.errors) == 0
        assert_local_download_data(syn_data, expect=all_syn_entities)
        # TODO: assert compared


async def test_it_downloads_and_compares_a_single_file(syn_data, assert_local_download_data, reset_download_dir):
    syn_file0 = syn_data['syn_file0']
    syn_file0_local = syn_data['syn_file0_download_path']
    syn_file0_local_dir = os.path.dirname(syn_file0_local)

    # entity is file and path is a file.
    # This will pass but download to the wrong dir.
    downloader = Downloader(syn_file0.id, syn_file0_local, download=True, compare=True)
    await downloader.execute()
    assert len(downloader.errors) == 0
    with pytest.raises(AssertionError):
        assert_local_download_data(syn_data, expect=[syn_file0])

    # entity is file and path is a dir.
    reset_download_dir(syn_data)
    downloader = Downloader(syn_file0.id, syn_file0_local_dir, download=True, compare=True)
    await downloader.execute()
    assert len(downloader.errors) == 0
    assert_local_download_data(syn_data, expect=[syn_file0])


async def test_it_compares_everything(syn_data):
    download_dir = syn_data['upload_dir']
    project = syn_data['project']

    comparer = Downloader(project.id, download_dir, download=False, compare=True)
    await comparer.execute()
    assert len(comparer.errors) == 0

    # Delete a local file and folder
    local_folder = syn_data['folder2']
    local_file = syn_data['file0']
    os.remove(local_file)
    shutil.rmtree(local_folder)
    assert os.path.exists(local_folder) is False
    assert os.path.exists(local_file) is False
    comparer = Downloader(project.id, download_dir, download=False, compare=True)
    await comparer.execute()
    assert len(comparer.errors) == 2


async def test_it_compares_a_single_file(synapse_test_helper):
    local_dir = synapse_test_helper.create_temp_dir()
    local_file = synapse_test_helper.create_temp_file(dir=local_dir)
    project = synapse_test_helper.create_project()
    syn_file = synapse_test_helper.create_file(parent=project, path=local_file)

    # entity is file and path is a file.
    comparer = Downloader(syn_file.id, local_file, download=False, compare=True)
    await comparer.execute()
    assert len(comparer.errors) > 0
    assert comparer.errors[0] == 'Local path does not exist: {0}'.format(
        os.path.join(local_file, os.path.basename(local_file)))

    # entity is a container and path is a file.
    comparer = Downloader(project.id, local_file, download=False, compare=True)
    await comparer.execute()
    assert len(comparer.errors) > 0
    assert comparer.errors[0] == 'Download path must be a directory.'

    # entity is a file and path is a folder.
    comparer = Downloader(syn_file.id, local_dir, download=False, compare=True)
    await comparer.execute()
    assert len(comparer.errors) == 0

    # local file does not exist
    os.remove(local_file)
    comparer = Downloader(syn_file.id, local_dir, download=False, compare=True)
    await comparer.execute()
    assert len(comparer.errors) > 0
    assert comparer.errors[0] == 'Local path does not exist: {0}'.format(local_file)


async def test_it_excludes_folders_by_id(syn_data, assert_local_download_data, reset_download_dir):
    download_dir = syn_data['download_dir']
    project = syn_data['project']
    syn_file0 = syn_data['syn_file0']
    syn_folder1 = syn_data['syn_folder1']
    syn_file1 = syn_data['syn_file1']
    syn_folder2 = syn_data['syn_folder2']
    syn_file2 = syn_data['syn_file2']

    reset_download_dir(syn_data)
    downloader = Downloader(project.id, download_dir, excludes=[syn_folder1.id])
    await downloader.execute()
    assert len(downloader.errors) == 0
    assert_local_download_data(syn_data,
                               expect=[syn_file0],
                               not_expect=[syn_folder1, syn_file1, syn_folder2, syn_file2])

    reset_download_dir(syn_data)
    downloader = Downloader(project.id, download_dir, excludes=[syn_folder2.id])
    await downloader.execute()
    assert len(downloader.errors) == 0
    assert_local_download_data(syn_data,
                               expect=[syn_file0, syn_folder1, syn_file1],
                               not_expect=[syn_folder2, syn_file2])


async def test_it_excludes_folders_by_name(syn_data, assert_local_download_data, reset_download_dir):
    download_dir = syn_data['download_dir']
    project = syn_data['project']
    syn_file0 = syn_data['syn_file0']
    syn_folder1 = syn_data['syn_folder1']
    syn_file1 = syn_data['syn_file1']
    syn_folder2 = syn_data['syn_folder2']
    syn_file2 = syn_data['syn_file2']

    reset_download_dir(syn_data)
    downloader = Downloader(project.id, download_dir, excludes=[syn_folder1.name])
    await downloader.execute()
    assert len(downloader.errors) == 0
    assert_local_download_data(syn_data,
                               expect=[syn_file0],
                               not_expect=[syn_folder1, syn_file1, syn_folder2, syn_file2])

    reset_download_dir(syn_data)
    downloader = Downloader(project.id, download_dir, excludes=[syn_folder2.name])
    await downloader.execute()
    assert len(downloader.errors) == 0
    assert_local_download_data(syn_data,
                               expect=[syn_file0, syn_folder1, syn_file1],
                               not_expect=[syn_folder2, syn_file2])


async def test_it_excludes_files_by_id(syn_data, assert_local_download_data, reset_download_dir):
    download_dir = syn_data['download_dir']
    project = syn_data['project']
    all_syn_entities = syn_data['all_syn_entities']
    all_syn_folders = syn_data['all_syn_folders']
    all_syn_files = syn_data['all_syn_files']

    # Exclude each file
    for syn_file in all_syn_files:
        reset_download_dir(syn_data)
        downloader = Downloader(project.id, download_dir, excludes=[syn_file.id])
        await downloader.execute()
        expected = all_syn_entities.copy()
        expected.remove(syn_file)
        assert len(downloader.errors) == 0
        assert_local_download_data(syn_data,
                                   expect=expected,
                                   not_expect=[syn_file])

    # Exclude all files
    reset_download_dir(syn_data)
    downloader = Downloader(project.id, download_dir, excludes=[f.id for f in all_syn_files])
    await downloader.execute()
    assert len(downloader.errors) == 0
    assert_local_download_data(syn_data,
                               expect=all_syn_folders,
                               not_expect=all_syn_files)


async def test_it_excludes_files_by_name(syn_data, assert_local_download_data, reset_download_dir):
    download_dir = syn_data['download_dir']
    project = syn_data['project']
    all_syn_entities = syn_data['all_syn_entities']
    all_syn_folders = syn_data['all_syn_folders']
    all_syn_files = syn_data['all_syn_files']

    # Exclude each file
    for syn_file in all_syn_files:
        reset_download_dir(syn_data)
        downloader = Downloader(project.id, download_dir, excludes=[syn_file.name])
        await downloader.execute()
        expected = all_syn_entities.copy()
        expected.remove(syn_file)
        assert len(downloader.errors) == 0
        assert_local_download_data(syn_data,
                                   expect=expected,
                                   not_expect=[syn_file])

    # Exclude all files
    reset_download_dir(syn_data)
    downloader = Downloader(project.id, download_dir, excludes=[f.name for f in all_syn_files])
    await downloader.execute()
    assert len(downloader.errors) == 0
    assert_local_download_data(syn_data,
                               expect=all_syn_folders,
                               not_expect=all_syn_files)


async def test_it_excludes_files_by_filename(syn_data, assert_local_download_data, reset_download_dir):
    download_dir = syn_data['download_dir']
    project = syn_data['project']
    all_syn_entities = syn_data['all_syn_entities']
    all_syn_folders = syn_data['all_syn_folders']
    all_syn_files = syn_data['all_syn_files']

    # Exclude each file
    for syn_file in all_syn_files:
        reset_download_dir(syn_data)
        downloader = Downloader(project.id, download_dir, excludes=[syn_file._file_handle.fileName])
        await downloader.execute()
        expected = all_syn_entities.copy()
        expected.remove(syn_file)
        assert len(downloader.errors) == 0
        assert_local_download_data(syn_data, expect=expected, not_expect=[syn_file])

    # Exclude all files
    reset_download_dir(syn_data)
    downloader = Downloader(project.id, download_dir, excludes=[f._file_handle.fileName for f in all_syn_files])
    await downloader.execute()
    assert len(downloader.errors) == 0
    assert_local_download_data(syn_data,
                               expect=all_syn_folders,
                               not_expect=all_syn_files)

# TODO: test downloading files of: 'concreteType': 'org.sagebionetworks.repo.model.file.ExternalFileHandle'

# TODO: Add additional tests...
