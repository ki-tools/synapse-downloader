import os
import argparse
import logging
from datetime import datetime
from .download import Downloader
from .core import Utils, SynapseProxy
from .compare.comparer import Comparer
from ._version import __version__


def _start_download(args):
    Downloader(args.entity_id,
               args.download_path,
               args.exclude,
               with_view=args.with_view,
               username=args.username,
               password=args.password).start()


def _start_compare(args):
    Comparer(args.entity_id,
             args.download_path,
             with_view=args.with_view,
             ignores=args.compare_ignore,
             username=args.username,
             password=args.password).start()


def main(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', action='version', version='%(prog)s {0}'.format(__version__))
    parser.add_argument('entity_id',
                        metavar='entity-id',
                        help='The ID of the Synapse entity to download or compare (Project, Folder or File).')

    parser.add_argument('download_path',
                        metavar='download-path',
                        help='The local path to save the files to or to compare.')

    parser.add_argument('-e', '--exclude',
                        help='Items to exclude from download. Synapse IDs or names (names are case-sensitive).',
                        action='append', nargs='?')

    parser.add_argument('-u', '--username',
                        help='Synapse username.',
                        default=None)

    parser.add_argument('-p', '--password',
                        help='Synapse password.',
                        default=None)

    parser.add_argument('-ll', '--log-level',
                        help='Set the logging level.',
                        default='INFO')

    parser.add_argument('-ld', '--log-dir',
                        help='Set the directory where the log file will be written.')

    parser.add_argument('-dt', '--download-timeout',
                        help='Set the maximum time (in seconds) a file can download before it is canceled.',
                        type=int,
                        default=SynapseProxy.Aio.FILE_DOWNLOAD_TIMEOUT)

    parser.add_argument('-w', '--with-view',
                        help='Use an entity view for loading file info. Fastest for large projects.',
                        default=False,
                        action='store_true')

    parser.add_argument('-wc', '--with-compare',
                        help='Run the comparison after downloading everything.',
                        default=False,
                        action='store_true')

    # Comparing.
    parser.add_argument('-c', '--compare',
                        help='Compare a local directory against a remote project or folder.',
                        default=False,
                        action='store_true')

    parser.add_argument('-ci', '--compare-ignore',
                        help='Path to directories or files to ignore when comparing.',
                        action='append',
                        nargs='?')

    args = parser.parse_args(args)

    log_level = getattr(logging, args.log_level.upper())

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    log_filename = '{0}.log'.format(timestamp)

    if args.log_dir:
        log_filename = os.path.join(Utils.expand_path(args.log_dir), log_filename)
    else:
        log_filename = os.path.join(Utils.app_log_dir(), log_filename)

    Utils.ensure_dirs(os.path.dirname(log_filename))

    logging.basicConfig(
        filename=log_filename,
        filemode='w',
        format='%(asctime)s %(levelname)s: %(message)s',
        level=log_level
    )

    # Add console logging.
    console = logging.StreamHandler()
    console.setLevel(log_level)
    console.setFormatter(logging.Formatter('%(message)s'))
    logging.getLogger().addHandler(console)

    print('Logging output to: {0}'.format(log_filename))

    if args.download_timeout != SynapseProxy.Aio.FILE_DOWNLOAD_TIMEOUT:
        SynapseProxy.Aio.FILE_DOWNLOAD_TIMEOUT = args.download_timeout
        logging.info('Download timeout set to: {0}'.format(SynapseProxy.Aio.FILE_DOWNLOAD_TIMEOUT))

    if args.compare:
        _start_compare(args)
    else:
        _start_download(args)
        if args.with_compare:
            _start_compare(args)

    print('Output logged to: {0}'.format(log_filename))


if __name__ == "__main__":
    main()
