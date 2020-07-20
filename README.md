[![Build Status](https://travis-ci.org/ki-tools/synapse-downloader.svg?branch=master)](https://travis-ci.org/ki-tools/synapse-downloader)
[![Coverage Status](https://coveralls.io/repos/github/ki-tools/synapse-downloader/badge.svg?branch=master)](https://coveralls.io/github/ki-tools/synapse-downloader?branch=master)

# Synapse Downloader

Utility for downloading large datasets from Synapse.

## Dependencies

- [Python3.7](https://www.python.org/)
- A [Synapse](https://www.synapse.org/) account with a username/password. Authentication through a 3rd party (.e.g., Google) will not work, you must have a Synapse user/pass for the [API to authenticate](http://docs.synapse.org/python/#connecting-to-synapse).

## Install

```bash
pip install synapse-downloader
```

## Configuration

Your Synapse credential can be provided on the command line (`--username`, `--password`) or via environment variables.

```bash
SYNAPSE_USERNAME=your-synapse-username
SYNAPSE_PASSWORD=your-synapse-password
```

## Usage

```text
usage: synapse-downloader [-h] [-e [EXCLUDE]] [-u USERNAME] [-p PASSWORD]
                          [-ll LOG_LEVEL] [-ld LOG_DIR] [-dt DOWNLOAD_TIMEOUT]
                          [-w] [-wc] [-c] [-ci [COMPARE_IGNORE]]
                          entity-id download-path

positional arguments:
  entity-id             The ID of the Synapse entity to download or compare
                        (Project, Folder or File).
  download-path         The local path to save the files to or to compare.

optional arguments:
  -h, --help            show this help message and exit
  -e [EXCLUDE], --exclude [EXCLUDE]
                        Items to exclude from download. Synapse IDs or names
                        (names are case-sensitive).
  -u USERNAME, --username USERNAME
                        Synapse username.
  -p PASSWORD, --password PASSWORD
                        Synapse password.
  -ll LOG_LEVEL, --log-level LOG_LEVEL
                        Set the logging level.
  -ld LOG_DIR, --log-dir LOG_DIR
                        Set the directory where the log file will be written.
  -dt DOWNLOAD_TIMEOUT, --download-timeout DOWNLOAD_TIMEOUT
                        Set the maximum time (in seconds) a file can download
                        before it is canceled.
  -w, --with-view       Use an entity view for loading file info. Fastest for
                        large projects.
  -wc, --with-compare   Run the comparison after downloading everything.
  -c, --compare         Compare a local directory against a remote project or
                        folder.
  -ci [COMPARE_IGNORE], --compare-ignore [COMPARE_IGNORE]
                        Path to directories or files to ignore when comparing.
```

## Development Setup

```bash
pipenv --three
pipenv shell
make pip_install
make build
make install_local
```
See [Makefile](Makefile) for all commands.
