import pytest
from src.synapse_downloader.cli import main


def test_cli():
    main(['syn18406882', '/tmp/syn-download', '-s', 'basic'])
