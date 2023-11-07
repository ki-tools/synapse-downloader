[![Build Status](https://travis-ci.org/ki-tools/synapse-downloader.svg?branch=master)](https://travis-ci.org/ki-tools/synapse-downloader)
[![Coverage Status](https://coveralls.io/repos/github/ki-tools/synapse-downloader/badge.svg?branch=master)](https://coveralls.io/github/ki-tools/synapse-downloader?branch=master)

# Synapse Downloader

Utility for downloading large datasets from Synapse.

## Dependencies

- [Python3.10+](https://www.python.org/)
- A [Synapse](https://www.synapse.org/) account with an auth token.

## Install

```bash
pip install synapse-downloader
```

## Configuration

### Environment Variables

No configuration is necessary if using environment variables or the default synapse config file.

For user/pass, set:

```shell
SYNAPSE_USERNAME=
SYNAPSE_PASSWORD=
```

For auth token, set:

```shell
SYNAPSE_AUTH_TOKEN=
```

For Synapse Config file:

Have a valid config file in: `~/.synapseConfig`

Or, have the environment variable set: `SYNAPSE_CONFIG_FILE=`

### Command Line Arguments

```text
options:
  -u USERNAME, --username USERNAME
                        Synapse username.
  -p PASSWORD, --password PASSWORD
                        Synapse password.
  --auth-token AUTH_TOKEN
                        Synapse auth token.
  --synapse-config SYNAPSE_CONFIG
                        Path to Synapse configuration file.
```

## Usage

```text
usage: synapse-downloader [-h] [--version] {download,compare,sync-from-synapse} ...

Synapse Downloader

options:
  -h, --help            show this help message and exit
  --version             show program's version number and exit

Commands:
  {download,compare,sync-from-synapse}
    download            Download items from Synapse to a local directory. Default command.
    compare             Compare items in Synapse to a local directory.
    sync-from-synapse   Download items from Synapse to a local directory using the syncFromSynapse method.
```

### Download

```text
usage: synapse-downloader download [-h] [-u USERNAME] [-p PASSWORD] [--auth-token AUTH_TOKEN]
                                   [--synapse-config SYNAPSE_CONFIG] [-ll LOG_LEVEL] [-ld LOG_DIR] [-e [EXCLUDE]] [-wc]
                                   entity-id local-path

positional arguments:
  entity-id             The ID of the Synapse entity to download (Project, Folder or File).
  local-path            The local path to save the files to.

options:
  -h, --help            show this help message and exit
  -u USERNAME, --username USERNAME
                        Synapse username.
  -p PASSWORD, --password PASSWORD
                        Synapse password.
  --auth-token AUTH_TOKEN
                        Synapse auth token.
  --synapse-config SYNAPSE_CONFIG
                        Path to Synapse configuration file.
  -ll LOG_LEVEL, --log-level LOG_LEVEL
                        Set the logging level.
  -ld LOG_DIR, --log-dir LOG_DIR
                        Set the directory where the log file will be written.
  -e [EXCLUDE], --exclude [EXCLUDE]
                        Items to exclude from download. Synapse IDs, names, or filenames (names are case-sensitive).
  -wc, --with-compare   Run compare after downloading everything.

```

### Compare

```text
usage: synapse-downloader compare [-h] [-u USERNAME] [-p PASSWORD] [--auth-token AUTH_TOKEN] [--synapse-config SYNAPSE_CONFIG]
                                  [-ll LOG_LEVEL] [-ld LOG_DIR] [-e [EXCLUDE]]
                                  entity-id local-path

positional arguments:
  entity-id             The ID of the Synapse entity to compare (Project, Folder or File).
  local-path            The local path to compare.

options:
  -h, --help            show this help message and exit
  -u USERNAME, --username USERNAME
                        Synapse username.
  -p PASSWORD, --password PASSWORD
                        Synapse password.
  --auth-token AUTH_TOKEN
                        Synapse auth token.
  --synapse-config SYNAPSE_CONFIG
                        Path to Synapse configuration file.
  -ll LOG_LEVEL, --log-level LOG_LEVEL
                        Set the logging level.
  -ld LOG_DIR, --log-dir LOG_DIR
                        Set the directory where the log file will be written.
  -e [EXCLUDE], --exclude [EXCLUDE]
                        Items to exclude from compare. Synapse IDs, names, or filenames (names are case-sensitive).
```

### Sync From Synapse

```text
usage: synapse-downloader sync-from-synapse [-h] [-u USERNAME] [-p PASSWORD] [--auth-token AUTH_TOKEN]
                                            [--synapse-config SYNAPSE_CONFIG] [-ll LOG_LEVEL] [-ld LOG_DIR]
                                            entity-id local-path

positional arguments:
  entity-id             The ID of the Synapse entity to download (Project, Folder or File).
  local-path            The local path to save the files to.

options:
  -h, --help            show this help message and exit
  -u USERNAME, --username USERNAME
                        Synapse username.
  -p PASSWORD, --password PASSWORD
                        Synapse password.
  --auth-token AUTH_TOKEN
                        Synapse auth token.
  --synapse-config SYNAPSE_CONFIG
                        Path to Synapse configuration file.
  -ll LOG_LEVEL, --log-level LOG_LEVEL
                        Set the logging level.
  -ld LOG_DIR, --log-dir LOG_DIR
                        Set the directory where the log file will be written.
```

## Development Setup

```bash
pipenv --python 3.10
pipenv shell
make pip_install
make build
make install_local
```

See [Makefile](Makefile) for all commands.

Run tests:

1. Rename `.env.template` to `.env` and set the variables in the file.
2. Run `make test` or `tox`
