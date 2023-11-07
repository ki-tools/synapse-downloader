import pytest
from src.synapse_downloader.core import Env


def test_it_returns_the_values(monkeypatch):
    env_vars = [
        ['SYNTOOLS_PATCH', False],
        ['SYNTOOLS_SYN_GET_DOWNLOAD', False],
        ['SYNTOOLS_DOWNLOAD_WORKERS', 20],
        ['SYNTOOLS_DOWNLOAD_RETRIES', 10]
    ]

    def reset():
        for var, value in env_vars:
            setattr(Env, "_{0}".format(var), None)

    for var, value in env_vars:
        reset()
        monkeypatch.delenv(var, raising=False)
        assert getattr(Env, var)() == value

        reset()
        monkeypatch.setenv(var, str(value))
        assert getattr(Env, var)() == value

        reset()
        if value in [True, False]:
            new_value = not value
        else:
            new_value = value + 5
        monkeypatch.setenv(var, str(new_value))
        assert getattr(Env, var)() == new_value
