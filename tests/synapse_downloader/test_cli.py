import pytest
from src.synapse_downloader.cli import main


def test_cli():
    main(['syn21064576', '/tmp/syn-download', '-c'])
