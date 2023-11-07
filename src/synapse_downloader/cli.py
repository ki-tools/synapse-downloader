import os
import sys
import argparse
import logging
import asyncio
from datetime import datetime
from .core import Utils
from .commands.download import cli as download_cli
from .commands.sync_from_synapse import cli as sync_from_synapse_cli
from ._version import __version__
from synapsis import cli as synapsis_cli

ALL_COMMANDS = [download_cli, sync_from_synapse_cli]


class LogFilter(logging.Filter):
    FILTERS = [
        'Connection pool is full, discarding connection:'
    ]

    def filter(self, record):
        for filter in self.FILTERS:
            if filter in record.msg:
                return False
        return True


def main():
    Utils.patch()
    main_parser = argparse.ArgumentParser(description='Synapse Downloader')
    main_parser.add_argument('--version', action='version', version='%(prog)s {0}'.format(__version__))

    shared_parser = argparse.ArgumentParser(add_help=False)
    synapsis_cli.inject(shared_parser)
    shared_parser.add_argument('-ll', '--log-level', help='Set the logging level.', default='INFO')
    shared_parser.add_argument('-ld', '--log-dir', help='Set the directory where the log file will be written.')

    subparsers = main_parser.add_subparsers(title='Commands', dest='command')
    for command in ALL_COMMANDS:
        command.create(subparsers, [shared_parser])

    if len(sys.argv) >= 2:
        first_arg = sys.argv[1]
        if first_arg not in ['download', 'compare', 'sync-from-synapse'] and first_arg not in ['-h', '--help',
                                                                                               '-v', '--version']:
            sys.argv.insert(1, 'download')

    cmd_args = main_parser.parse_args()

    if '_new_command' in cmd_args:
        log_level = getattr(logging, cmd_args.log_level.upper())
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        log_filename = '{0}.log'.format(timestamp)

        if cmd_args.log_dir:
            log_filename = os.path.join(Utils.expand_path(cmd_args.log_dir), log_filename)
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
        console = logging.StreamHandler(stream=sys.stdout)
        console.setLevel(log_level)
        console.setFormatter(logging.Formatter('%(message)s'))
        logging.getLogger().addHandler(console)

        # TODO: Fix "Connection pool is full, discarding connection:" and remove the log filter.
        log_filter = LogFilter()
        for logger in [logging.getLogger(name) for name in logging.root.manager.loggerDict]:
            logger.addFilter(log_filter)

        print('Logging output to: {0}'.format(log_filename))
        exit_code = 1
        try:
            synapsis_cli.configure(cmd_args, synapse_args={'multi_threaded': False}, login=True)
            cmd = cmd_args._new_command(cmd_args)
            try:
                asyncio.run(cmd.execute())
            except KeyboardInterrupt:
                cmd.abort()

            print('')
            if cmd.errors:
                exit_code = 1
                logging.error('Finished with errors:')
                for error in cmd.errors:
                    logging.error(' - {0}'.format(error))
            else:
                exit_code = 0
                logging.info('Finished Successfully.')
        except Exception as ex:
            exit_code = 1
            logging.error(ex)
            logging.error('Finished with errors.')

        print('Output logged to: {0}'.format(log_filename))
        sys.exit(exit_code)
    else:
        main_parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
