from .synapse_downloader import SynapseDownloader
from .synapse_downloader_file_view import SynapseDownloaderFileView
from .synapse_downloader_file_view_no_aio import SynapseDownloaderFileViewNoAio
from .synapse_downloader_old import SynapseDownloaderOld
from .synapse_downloader_sync import SynapseDownloaderSync
import argparse
import logging


def main(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('entity_id', metavar='entity-id',
                        help='The ID of the Synapse entity to download (Project or Folder).')
    parser.add_argument('download_path', metavar='download-path', help='The local path to save the files to.')
    parser.add_argument('-u', '--username', help='Synapse username.', default=None)
    parser.add_argument('-p', '--password', help='Synapse password.', default=None)
    parser.add_argument('-l', '--log-level', help='Set the logging level.', default='INFO')

    parser.add_argument('-s', '--strategy', help='Use the new or old download strategy', default='new-file-view',
                        choices=['new', 'new-file-view', 'new-file-view-no-aio', 'old', 'sync'])

    args = parser.parse_args(args)

    log_level = getattr(logging, args.log_level.upper())
    log_filename = 'log.txt'

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

    if args.strategy == 'old':
        SynapseDownloaderOld(args.entity_id,
                             args.download_path,
                             username=args.username,
                             password=args.password).execute()
    elif args.strategy == 'sync':
        SynapseDownloaderSync(args.entity_id,
                              args.download_path,
                              username=args.username,
                              password=args.password).execute()
    elif args.strategy == 'new':
        SynapseDownloader(args.entity_id,
                          args.download_path,
                          username=args.username,
                          password=args.password).execute()

    elif args.strategy == 'new-file-view-no-aio':
        SynapseDownloaderFileViewNoAio(args.entity_id,
                                       args.download_path,
                                       username=args.username,
                                       password=args.password).execute()
    else:
        SynapseDownloaderFileView(args.entity_id,
                                  args.download_path,
                                  username=args.username,
                                  password=args.password).execute()


if __name__ == "__main__":
    main()
