import pytest
import os
from src.synapse_downloader.core import SynapseItem
from synapsis import Synapsis


async def test_it_loads(synapse_test_helper):
    local_root_path = synapse_test_helper.create_temp_dir()
    synapse_root_path = ''

    syn_project = synapse_test_helper.create_project()
    for project_item in [
        SynapseItem(syn_project,
                    synapse_root_path=synapse_root_path,
                    local_root_path=local_root_path),
        SynapseItem(Synapsis.ConcreteTypes.PROJECT_ENTITY,
                    id=syn_project.id,
                    name=syn_project.name,
                    synapse_root_path=synapse_root_path,
                    local_root_path=local_root_path)
    ]:
        assert project_item.exists is True
        assert project_item.is_loaded is True
        load_result = await project_item.load()
        assert load_result == project_item
        assert project_item.is_loaded is True
        assert project_item.is_project
        assert project_item.is_folder is False
        assert project_item.is_file is False
        assert project_item.parent_id in [None, syn_project.id]
        assert project_item.id == syn_project.id
        assert project_item.synapse_path == syn_project.name
        assert project_item.name == syn_project.name
        assert project_item.local.abs_path == project_item.local_root_path
        assert project_item.local.name == os.path.basename(project_item.local_root_path)
        assert project_item.local.exists
        assert project_item.local.is_dir
        assert project_item.local.is_file is False
        assert project_item.local.content_size is None
        assert project_item.local.content_md5 is None
        assert await project_item.local.content_md5_async() is None

    syn_folder = synapse_test_helper.create_folder(parent=syn_project, name='Folder1')
    for folder_item in [
        SynapseItem(syn_folder,
                    synapse_root_path=project_item.synapse_path,
                    local_root_path=project_item.local.abs_path),
        SynapseItem(Synapsis.ConcreteTypes.FOLDER_ENTITY,
                    id=syn_folder.id,
                    parent_id=syn_folder.parentId,
                    name=syn_folder.name,
                    synapse_root_path=project_item.synapse_path,
                    local_root_path=project_item.local.abs_path)
    ]:
        assert folder_item.exists is True
        assert folder_item.is_loaded is True
        load_result = await folder_item.load()
        assert load_result == folder_item
        assert folder_item.is_loaded is True
        assert folder_item.parent_id == syn_folder.parentId
        assert folder_item.id == syn_folder.id
        assert folder_item.synapse_path == project_item.synapse_path + '/' + syn_folder.name
        assert folder_item.name == syn_folder.name
        assert folder_item.local.abs_path == os.path.join(project_item.local.abs_path, syn_folder.name)
        assert folder_item.local.exists is False
        os.mkdir(folder_item.local.abs_path)
        assert folder_item.local.exists
        assert folder_item.local.is_dir
        assert folder_item.local.is_file is False
        os.rmdir(folder_item.local.abs_path)

    syn_file = synapse_test_helper.create_file(parent=syn_folder, name='File1')
    for file_item in [
        SynapseItem(syn_file,
                    synapse_root_path=folder_item.synapse_path,
                    local_root_path=folder_item.local.abs_path
                    ),
        SynapseItem(Synapsis.ConcreteTypes.FILE_ENTITY,
                    id=syn_file.id,
                    parent_id=syn_file.parentId,
                    name=syn_file.name,
                    synapse_root_path=folder_item.synapse_path,
                    local_root_path=folder_item.local.abs_path
                    )
    ]:
        assert file_item.exists is True

        if file_item.file_handle_id is None:
            assert file_item.is_loaded is False
        else:
            assert file_item.is_loaded

        load_result = await file_item.load()
        assert load_result == file_item
        assert file_item.is_loaded is True
        assert file_item.parent_id == syn_file.parentId
        assert file_item.id == syn_file.id
        assert file_item.synapse_path == folder_item.synapse_path + '/' + syn_file.name
        assert file_item.name == syn_file.name
        assert file_item.file_handle_id == syn_file.dataFileHandleId
        assert file_item.local.abs_path == os.path.join(folder_item.local.abs_path,
                                                        syn_file['_file_handle']['fileName'])
        assert file_item.local.exists == os.path.exists(file_item.local.abs_path)
        if not os.path.exists(file_item.local.abs_path):
            tmp_file = synapse_test_helper.create_temp_file(syn_file['_file_handle']['fileName'],
                                                            dir=file_item.local.dirname)
            assert tmp_file == file_item.local.abs_path
        assert file_item.local.exists
        assert file_item.local.is_file
        assert file_item.local.is_dir is False
