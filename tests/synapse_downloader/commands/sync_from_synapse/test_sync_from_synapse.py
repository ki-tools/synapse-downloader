import pytest
from synapse_downloader.commands.sync_from_synapse import SyncFromSynapse


async def test_it_downloads_everything(syn_data, assert_local_download_data, reset_download_dir):
    reset_download_dir(syn_data)
    download_dir = syn_data['download_dir']
    project = syn_data['project']
    all_syn_entities = syn_data['all_syn_entities']

    downloader = SyncFromSynapse(project.id, download_dir)
    await downloader.execute()
    assert len(downloader.errors) == 0
    assert_local_download_data(syn_data, expect=all_syn_entities)
