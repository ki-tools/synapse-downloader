import pytest
import src.synapse_downloader.cli as cli
from src.synapse_downloader.download import Downloader
from src.synapse_downloader.compare import Comparer


def test_download_with_compare_cli(mocker):
    args = ['', 'syn123', '/tmp', '-e', 'syn1234', '-u', 'user', '-p', 'pass', '-ll', 'DEBUG', '-ld', '/tmp/logs',
            '-dt', '30', '-w', '-wc', '-ci', 'syn12345']
    mocker.patch('sys.argv', args)
    mocker.patch('src.synapse_downloader.download.Downloader.start')
    mocker.patch('src.synapse_downloader.compare.Comparer.start')
    mock_init_download = mocker.spy(Downloader, '__init__')
    mock_init_compare = mocker.spy(Comparer, '__init__')

    with pytest.raises(SystemExit):
        cli.main()

    mock_init_download.assert_called_once_with(mocker.ANY,
                                               'syn123',
                                               '/tmp',
                                               excludes=['syn1234'],
                                               with_view=True,
                                               username='user',
                                               password='pass'
                                               )

    mock_init_compare.assert_called_once_with(mocker.ANY,
                                              'syn123',
                                              '/tmp',
                                              with_view=True,
                                              ignores=['syn12345'],
                                              username='user',
                                              password='pass'
                                              )


def test_compare_cli(mocker):
    args = ['', 'syn123', '/tmp', '-e', 'syn1234', '-u', 'user', '-p', 'pass', '-ll', 'DEBUG', '-ld', '/tmp/logs',
            '-dt', '30', '-w', '-wc', '-ci', 'syn12345', '-c']
    mocker.patch('sys.argv', args)
    mocker.patch('src.synapse_downloader.download.Downloader.start')
    mocker.patch('src.synapse_downloader.compare.Comparer.start')
    mock_init_download = mocker.spy(Downloader, '__init__')
    mock_init_compare = mocker.spy(Comparer, '__init__')

    with pytest.raises(SystemExit):
        cli.main()

    mock_init_download.assert_not_called()

    mock_init_compare.assert_called_once_with(mocker.ANY,
                                              'syn123',
                                              '/tmp',
                                              with_view=True,
                                              ignores=['syn12345'],
                                              username='user',
                                              password='pass'
                                              )
