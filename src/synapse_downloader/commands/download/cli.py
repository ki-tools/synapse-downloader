from .downloader import Downloader


def create(subparsers, parents):
    for command in ['download', 'compare']:
        if command == 'download':
            help = 'Download items from Synapse to a local directory. Default command.'
        else:
            help = 'Compare items in Synapse to a local directory.'
        parser = subparsers.add_parser(command, parents=parents, help=help)

        if command == 'download':
            help = 'The ID of the Synapse entity to download (Project, Folder or File).'
        else:
            help = 'The ID of the Synapse entity to compare (Project, Folder or File).'
        parser.add_argument('entity_id',
                            metavar='entity-id',
                            help=help)

        if command == 'download':
            help = 'The local path to save the files to.'
        else:
            help = 'The local path to compare.'
        parser.add_argument('local_path',
                            metavar='local-path',
                            help=help)

        if command == 'download':
            help = 'Items to exclude from download. Synapse IDs, names, or filenames (names are case-sensitive).'
        else:
            help = 'Items to exclude from compare. Synapse IDs, names, or filenames (names are case-sensitive).'
        parser.add_argument('-e', '--exclude', help=help, action='append', nargs='?')

        if command == 'download':
            parser.add_argument('-wc', '--with-compare',
                                help='Run compare after downloading everything.',
                                default=False,
                                action='store_true')

        parser.set_defaults(_new_command=new_command)


def new_command(args):
    do_download = args.command == 'download'
    do_compare = args.command == 'compare' or ('with_compare' in args and args.with_compare)
    return Downloader(args.entity_id,
                      args.local_path,
                      download=do_download,
                      compare=do_compare,
                      excludes=args.exclude
                      )
