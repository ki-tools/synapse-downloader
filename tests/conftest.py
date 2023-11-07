import pytest
import os
import shutil
from synapse_test_helper import SynapseTestHelper
from synapsis import Synapsis
import synapseclient as syn
from dotenv import load_dotenv

load_dotenv(override=True)


@pytest.fixture(scope='session')
def test_synapse_auth_token():
    return os.environ.get('SYNAPSE_AUTH_TOKEN')


@pytest.fixture(scope='session', autouse=True)
def syn_client(test_synapse_auth_token):
    Synapsis.configure(authToken=test_synapse_auth_token, synapse_args={'multi_threaded': False})
    SynapseTestHelper.configure(Synapsis.login().Synapse)
    return Synapsis.Synapse


@pytest.fixture()
def synapse_test_helper():
    with SynapseTestHelper() as sth:
        yield sth


@pytest.fixture(scope='module')
def syn_data():
    with SynapseTestHelper() as synapse_test_helper:
        download_dir = synapse_test_helper.create_temp_dir(prefix='download_dir_')
        upload_dir = synapse_test_helper.create_temp_dir(prefix='upload_dir_')

        project = synapse_test_helper.create_project(prefix='Project-')
        file0 = synapse_test_helper.create_temp_file(name='File0.txt', dir=upload_dir)
        syn_file0 = synapse_test_helper.create_file(path=file0, parent=project)

        syn_folder1 = synapse_test_helper.create_folder(name='Folder1', parent=project)
        folder1 = os.path.join(upload_dir, syn_folder1.name)
        file1 = synapse_test_helper.create_temp_file(name='File1.txt', dir=folder1)
        syn_file1 = synapse_test_helper.create_file(path=file1, parent=syn_folder1)

        syn_folder2 = synapse_test_helper.create_folder(name='Folder2', parent=syn_folder1)
        folder2 = os.path.join(upload_dir, syn_folder1.name, syn_folder2.name)
        file2 = synapse_test_helper.create_temp_file(name='File2.txt', dir=folder2)
        syn_file2 = synapse_test_helper.create_file(path=file2, parent=syn_folder2)

        syn_file0_download_path = os.path.join(download_dir, syn_file0._file_handle.fileName)
        syn_folder1_download_path = os.path.join(download_dir, syn_folder1.name)
        syn_file1_download_path = os.path.join(syn_folder1_download_path, syn_file1._file_handle.fileName)
        syn_folder2_download_path = os.path.join(syn_folder1_download_path, syn_folder2.name)
        syn_file2_download_path = os.path.join(syn_folder2_download_path, syn_file2._file_handle.fileName)

        result = {
            'download_dir': download_dir,
            'upload_dir': upload_dir,
            'project': project,
            'file0': file0,
            'folder1': folder1,
            'syn_file0': syn_file0,
            'syn_file0_download_path': syn_file0_download_path,
            'syn_folder1': syn_folder1,
            'syn_folder1_download_path': syn_folder1_download_path,
            'file1': file1,
            'syn_file1': syn_file1,
            'syn_file1_download_path': syn_file1_download_path,
            'folder2': folder2,
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

        yield result


@pytest.fixture
def reset_download_dir():
    def _reset(syn_data):
        download_dir = syn_data['download_dir']
        if os.path.isdir(download_dir):
            shutil.rmtree(download_dir)

    yield _reset


@pytest.fixture
def assert_local_download_data():
    def _a(syn_data, expect=[], not_expect=[]):
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

    yield _a
