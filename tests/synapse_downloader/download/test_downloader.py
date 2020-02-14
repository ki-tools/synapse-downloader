import pytest
import os
from src.synapse_downloader.download.downloader import Downloader


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
    return {
        'download_dir': download_dir,
        'project': project,
        'file0': file0,
        'syn_file0': syn_file0,
        'syn_folder1': syn_folder1,
        'file1': file1,
        'syn_file1': syn_file1,
        'syn_folder2': syn_folder2,
        'file2': file2,
        'syn_file2': syn_file2
    }


def assert_local_download_data(syn_data):
    download_dir = syn_data['download_dir']
    file0 = syn_data['file0']
    syn_folder1 = syn_data['syn_folder1']
    file1 = syn_data['file1']
    syn_folder2 = syn_data['syn_folder2']
    file2 = syn_data['file2']

    file0_local_path = os.path.join(download_dir, os.path.basename(file0))
    assert os.path.isfile(file0_local_path)

    folder1_local_path = os.path.join(download_dir, syn_folder1.name)
    assert os.path.isdir(folder1_local_path)

    file1_local_path = os.path.join(folder1_local_path, os.path.basename(file1))
    assert os.path.isfile(file1_local_path)

    folder2_local_path = os.path.join(folder1_local_path, syn_folder2.name)
    assert os.path.isdir(folder2_local_path)

    file2_local_path = os.path.join(folder2_local_path, os.path.basename(file2))
    assert os.path.isfile(file2_local_path)


def test_it_downloads_everything(syn_data):
    download_dir = syn_data['download_dir']
    project = syn_data['project']

    downloader = Downloader(project.id, download_dir)
    downloader.start()
    assert downloader.has_errors is False
    assert_local_download_data(syn_data)


def test_it_downloads_everything_with_entity_view(syn_data):
    download_dir = syn_data['download_dir']
    project = syn_data['project']

    downloader = Downloader(project.id, download_dir, with_view=True)
    downloader.start()
    assert downloader.has_errors is False
    # TODO: Figure out how to test the view was used.
    assert_local_download_data(syn_data)

# TODO: Add additional tests...
