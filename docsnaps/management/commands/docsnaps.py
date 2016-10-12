"""
Custom django-admin command with subcommands.

install
    Import a docsnaps plugin module and add its snapshot jobs to the docsnaps
    system.

run
    Check all active snapshot jobs and, if a document has changed since the last
    snapshot, a new snapshot will be taken.

"""

import argparse
from django.core.management.base import BaseCommand, CommandError
from importlib import import_module

from . import _install as subcommand_install
from . import _run as subcommand_run


class Command(BaseCommand):

    def add_arguments(self, parser):
        """
        Add arguments and subcommands to the argparse parser object.

        To my knowledge, this is the only "hook" Django provides into the
        argparse invocation. Therefore, I will add subcommands to the parser
        here despite the slight semantic mismatch of the task.

        The subparser's parser_class argument is necessary because Django has
        extended the argparse.ArgumentParser class and changed its interface.
        When add_parser() is called on the subparsers object, it attempts to
        instantiate Django's custom class rather than argparse's.

        See:
            https://docs.python.org/3.5/library/argparse.html#argparse.ArgumentParser.add_subparsers
            https://github.com/django/django/blob/master/django/core/management/base.py#L43

        """
        subparsers = parser.add_subparsers(parser_class=argparse.ArgumentParser)

        # "install" subcommand.
        install_parser = subparsers.add_parser(
            'install',
            help=subcommand_install.HELP)
        subcommand_install.add_arguments(install_parser)
        install_parser.set_defaults(handler=subcommand_install.handle)

        # "run" subcommand.
        run_parser = subparsers.add_parser(
            'run',
            help=subcommand_run.HELP)
        run_parser.set_defaults(handler=subcommand_run.handle)

    def handle(self, *args, **options):
        options['handler'](*args, **options)





