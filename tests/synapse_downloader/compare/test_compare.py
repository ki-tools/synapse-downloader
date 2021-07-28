import pytest
import os
from src.synapse_downloader.compare.comparer import Comparer


@pytest.fixture(scope='module')
def syn_data(syn_test_helper_class, mk_tempdir, write_file):
    source_dir = mk_tempdir()

    project = syn_test_helper_class.create_project(prefix='Project-')
    file0 = os.path.join(source_dir, 'file0.txt')
    write_file(file0)
    syn_file0 = syn_test_helper_class.create_file(name=os.path.basename(file0), path=file0, parent=project)

    folder1 = os.path.join(source_dir, 'folder1')
    syn_folder1 = syn_test_helper_class.create_folder(name=os.path.basename(folder1), parent=project)

    file1 = os.path.join(folder1, 'file1.txt')
    write_file(file1)
    syn_file1 = syn_test_helper_class.create_file(name=os.path.basename(file1), path=file1, parent=syn_folder1)

    folder2 = os.path.join(folder1, 'folder2')
    syn_folder2 = syn_test_helper_class.create_folder(name=os.path.basename(folder2), parent=syn_folder1)

    file2 = os.path.join(folder2, 'file2.txt')
    write_file(file2)
    syn_file2 = syn_test_helper_class.create_file(name=os.path.basename(file2), path=file2, parent=syn_folder2)

    return {
        'source_dir': source_dir,
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


def test_it_compares_everything(syn_data):
    source_dir = syn_data['source_dir']
    project = syn_data['project']

    comparer = Comparer(project.id, source_dir)
    comparer.start()
    assert len(comparer.errors) == 0


def test_it_compares_everything_with_entity_view(syn_data, capsys):
    source_dir = syn_data['source_dir']
    project = syn_data['project']

    comparer = Comparer(project.id, source_dir)
    comparer.start()
    assert len(comparer.errors) == 0
    # TODO: Figure out how to test the view was used.

# TODO: test comparing files of: 'concreteType': 'org.sagebionetworks.repo.model.file.ExternalFileHandle'

# TODO: Add additional tests...
