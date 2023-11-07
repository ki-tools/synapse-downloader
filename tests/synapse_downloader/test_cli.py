import pytest
import synapse_downloader.cli as cli
from synapse_downloader.commands.download import Downloader
from synapse_downloader.commands.sync_from_synapse import SyncFromSynapse


def test_download_command_as_default(mocker):
    args = ['<prog>',
            'syn123',
            '/tmp',
            '--exclude', 'syn1234',
            '--log-dir', '/tmp',
            '--log-level', 'DEBUG'
            ]
    mocker.patch('sys.argv', args)
    mocker.patch('src.synapse_downloader.commands.download.Downloader.execute')
    mock_init_download = mocker.spy(Downloader, '__init__')

    with pytest.raises(SystemExit):
        cli.main()

    mock_init_download.assert_called_once_with(mocker.ANY,
                                               'syn123',
                                               '/tmp',
                                               download=True,
                                               compare=False,
                                               excludes=['syn1234']
                                               )


def test_download_command(mocker):
    args = ['<prog>',
            'download',
            'syn123',
            '/tmp',
            '--exclude', 'syn1234',
            '--log-dir', '/tmp',
            '--log-level', 'DEBUG'
            ]
    mocker.patch('sys.argv', args)
    mocker.patch('synapse_downloader.commands.download.Downloader.execute')
    mock_init_download = mocker.spy(Downloader, '__init__')

    with pytest.raises(SystemExit):
        cli.main()

    mock_init_download.assert_called_once_with(mocker.ANY,
                                               'syn123',
                                               '/tmp',
                                               download=True,
                                               compare=False,
                                               excludes=['syn1234']
                                               )


def test_download_command_with_compare(mocker):
    args = ['<prog>',
            'download',
            'syn123',
            '/tmp',
            '--exclude', 'syn1234',
            '--with-compare',
            '--log-dir', '/tmp',
            '--log-level', 'DEBUG'
            ]
    mocker.patch('sys.argv', args)
    mocker.patch('src.synapse_downloader.commands.download.Downloader.execute')
    mock_init_download = mocker.spy(Downloader, '__init__')

    with pytest.raises(SystemExit):
        cli.main()

    mock_init_download.assert_called_once_with(mocker.ANY,
                                               'syn123',
                                               '/tmp',
                                               download=True,
                                               compare=True,
                                               excludes=['syn1234']
                                               )


def test_download_command_with_compare(mocker):
    args = ['<prog>',
            'compare',
            'syn123',
            '/tmp',
            '--exclude', 'syn1234',
            '--log-dir', '/tmp',
            '--log-level', 'DEBUG'
            ]
    mocker.patch('sys.argv', args)
    mocker.patch('src.synapse_downloader.commands.download.Downloader.execute')
    mock_init_download = mocker.spy(Downloader, '__init__')

    with pytest.raises(SystemExit):
        cli.main()

    mock_init_download.assert_called_once_with(mocker.ANY,
                                               'syn123',
                                               '/tmp',
                                               download=False,
                                               compare=True,
                                               excludes=['syn1234']
                                               )


def test_sync_from_synapse_command(mocker):
    args = ['<prog>',
            'sync-from-synapse',
            'syn123',
            '/tmp',
            '--log-dir', '/tmp',
            '--log-level', 'DEBUG'
            ]
    mocker.patch('sys.argv', args)
    mocker.patch('src.synapse_downloader.commands.sync_from_synapse.SyncFromSynapse.execute')
    mock_init_download = mocker.spy(SyncFromSynapse, '__init__')

    with pytest.raises(SystemExit):
        cli.main()

    mock_init_download.assert_called_once_with(mocker.ANY, 'syn123', '/tmp')
