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
from importlib import import_module

from django.core.management.base import BaseCommand, CommandError

from . import _install
# from . import _run as run_parser


class Command(BaseCommand):

    def __init__(self, stdout=None, stderr=None, no_color=False):
        """
        Override parent init method to create subcommand instances.

        I'm not sure about using **kwargs here. It seems like it might have
        hidden pitfalls so I'm going with a direct method signature copy for
        now.

        """
        super().__init__(stdout=stdout, stderr=stderr, no_color=no_color)
        self._install = _install.Command(
            stdout=stdout, stderr=stderr, no_color=no_color)

    def add_arguments(self, parser):
        """
        Add arguments and subcommands to the argparse parser object.

        To my knowledge, this is the only "hook" Django provides into the
        argparse invocation. Therefore, I will add subcommands to the parser
        here despite the slight semantic mismatch of the task.

        The subparser's parser_class argument is necessary because Django has
        extended the argparse.ArgumentParser class and changed its constructor
        signature. When add_parser() is called on the subparsers object, it
        attempts to instantiate Django's custom class rather than argparse's.

        The add_arguments function is a Django addition to the
        argparse.ArgumentParser interface.

        See:
            https://docs.python.org/3/library/argparse.html#argparse.ArgumentParser.add_subparsers
            https://github.com/django/django/blob/master/django/core/management/base.py#L43

        """
        subparsers = parser.add_subparsers(parser_class=argparse.ArgumentParser)

        # "install" subcommand.
        install_parser = subparsers.add_parser(
            'install',
            help=self._install.help)
        self._install.add_arguments(install_parser)
        install_parser.set_defaults(handler=self._install.handle)

        # "run" subcommand.
        # run_parser = subparsers.add_parser(
            # 'run',
            # help=subcommand_run.HELP)
        # run_parser.set_defaults(handler=subcommand_run.handle)

    def handle(self, *args, **options):
        options['handler'](*args, **options)





