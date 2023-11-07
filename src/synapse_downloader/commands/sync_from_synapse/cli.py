from .sync_from_synapse import SyncFromSynapse


def create(subparsers, parents):
    parser = subparsers.add_parser('sync-from-synapse',
                                   parents=parents,
                                   help='Download items from Synapse to a local directory using the syncFromSynapse method.')
    parser.add_argument('entity_id',
                        metavar='entity-id',
                        help='The ID of the Synapse entity to download (Project, Folder or File).')

    parser.add_argument('local_path',
                        metavar='local-path',
                        help='The local path to save the files to.')

    parser.set_defaults(_new_command=new_command)
    return parser


def new_command(args):
    return SyncFromSynapse(args.entity_id, args.local_path)
