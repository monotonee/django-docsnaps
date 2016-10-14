"""
A Django admin command that will install a new snapshot job.

All necessary data for the new job is loaded into the database.

"""

from importlib import import_module

from django.core.management.base import BaseCommand, CommandError
# , OutputWrapper



# Might not be needed if use CommandError instead.
# class InstallError(Exception):
    # """
    # An exception raised when something goes wrong during plugin install.

    # During the install process, many libraries' exceptions are caught and
    # messages output to stdout. I could re-raise the exceptions and be forced
    # to deal with myriad varieties of exception further down the stack or I could
    # raise a RuntimeError. However, I don't trust that I won't accidentally catch
    # a legitimate RuntimeError raised by an underlying library. Therefore, for
    # increased error handling granularity of only certain exceptional conditions,
    # I will use this custom exception for isolated internal error handling.

    # When a step in the install process raises this exception, it indicates that
    # the entire install procedure will end.

    # """


class Command(BaseCommand):

    help = 'Installs a new snapshot job and registers its transforms.'

    def _load_module(self, module_name):
        """
        Attempts to load the module passed as an argument to the subcommand.

        Returns:
            module: The module returned by importlib.import_module if successful.

        """
        self.stdout.write('Attempting to load module: ', ending='')
        try:
            module = import_module(module_name)
        except ImportError as import_error:
            self.stdout.write(self.style.ERROR('failed'))
            raise CommandError(import_error)
        else:
            self.stdout.write(self.style.SUCCESS('done'))
            return module

    def add_arguments(self, parser):
        parser.add_argument(
            'module',
            help='A fully-qualified, absolute path to a plugin module.',
            type=str)
        parser.add_argument(
            '-d', '--disabled',
            action='store_const',
            const=True,
            default=False,
            help='Install new doc snapshot job but leave it disabled.')

    def handle(self, *args, **options):
        """
        Load the passed module's data and register its transformers.

        Note: Attempting to dump the "args" variadic parameter in
        pdb will produce anomalous results. "args" is a pdb debugger command and
        takes precidence over dumping a variable's value.

        See:
            https://docs.python.org/3/library/pdb.html#pdbcommand-args

        """
        module = self._load_module(options['module'])

        # import pdb
        # pdb.set_trace()

        # Attempt to request all necessary models/data from the module.
        # If not complete data set, raise exception.
        # Check for transformer. Output found or not found.

        # language check, company, service, document, documentslanguages

        # Attempt to load al data within a single transaction.
            # Register module and its transformer.
            # Make sure to respect --disabled choice.
            # If storage error, roll back transaction and raise exception.












