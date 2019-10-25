import os
import argparse
import logging
from .utils import Utils
from .synapse_proxy import SynapseProxy
from .synapse_downloader import SynapseDownloader
from .synapse_downloader_old import SynapseDownloaderOld
from .synapse_downloader_sync import SynapseDownloaderSync
from .synapse_downloader_basic import SynapseDownloaderBasic
from .compare.synapse_comparer import SynapseComparer


def _start_compare(args):
    SynapseComparer(args.entity_id,
                    args.download_path,
                    with_view=args.with_view,
                    username=args.username,
                    password=args.password).start()


def main(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('entity_id',
                        metavar='entity-id',
                        help='The ID of the Synapse entity to download or compare (Project or Folder).')
    parser.add_argument('download_path',
                        metavar='download-path',
                        help='The local path to save the files to or to compare.')
    parser.add_argument('-u', '--username', help='Synapse username.', default=None)
    parser.add_argument('-p', '--password', help='Synapse password.', default=None)
    parser.add_argument('-ll', '--log-level', help='Set the logging level.', default='INFO')
    parser.add_argument('-lf', '--log-file', help='Set path to a log file.', default='log.txt')
    parser.add_argument('-dt', '--download-timeout',
                        help='Set the maximum time (in seconds) a file can download before it is canceled.',
                        type=int,
                        default=SynapseProxy.Aio.FILE_DOWNLOAD_TIMEOUT)
    parser.add_argument('-w', '--with-view',
                        help='Use an entity view for loading file info. Fastest for large projects. Only available for "-s new or basic" and "-c"',
                        default=False,
                        action='store_true')
    parser.add_argument('-s', '--strategy',
                        help='Use the new or old download strategy',
                        default='basic',
                        choices=['new', 'old', 'sync', 'basic'])

    parser.add_argument('-wc', '--with-compare',
                        help='Run the comparison after downloading everything.',
                        default=False,
                        action='store_true')

    # Comparing.
    parser.add_argument('-c', '--compare',
                        help='Compare a local directory against a remote project or folder.',
                        default=False,
                        action='store_true')
    # TODO: make this work.
    # parser.add_argument('-ci', '--compare-ignore', help='Path to directories or files to ignore when comparing.')

    args = parser.parse_args(args)

    log_level = getattr(logging, args.log_level.upper())
    log_filename = Utils.expand_path(args.log_file)
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
    elif args.strategy == 'new':
        SynapseDownloader(args.entity_id,
                          args.download_path,
                          with_view=args.with_view,
                          username=args.username,
                          password=args.password).start()
    elif args.strategy == 'old':
        SynapseDownloaderOld(args.entity_id,
                             args.download_path,
                             username=args.username,
                             password=args.password).start()
    elif args.strategy == 'sync':
        SynapseDownloaderSync(args.entity_id,
                              args.download_path,
                              username=args.username,
                              password=args.password).start()
    elif args.strategy == 'basic':
        SynapseDownloaderBasic(args.entity_id,
                               args.download_path,
                               with_view=args.with_view,
                               username=args.username,
                               password=args.password).start()

    if args.with_compare and not args.compare:
        _start_compare(args)


if __name__ == "__main__":
    main()
