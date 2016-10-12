"""
A Django admin command that will install a new snapshot job.

All necessary data for the new job is loaded into the database.

"""

from django.core.management.base import BaseCommand, CommandError
from importlib import import_module


HELP = 'Installs a new snapshot job and registers its transforms.'

def add_arguments(parser):
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

def handle(*args, **options):
    """
    Load the passed module's data and register its transformers.

    Note: Attempting to dump the "args" variadic parameter in
    pdb will produce anomalous results. "args" is a pdb debugger command and
    takes precidence over dumping a variable's value.

    See:
        https://docs.python.org/3/library/pdb.html#pdbcommand-args

    """
    # Attempt to find and load module.
    # If not found or loading error, raise exception.
    # Conscious choice to omit exeption handling for now. The resulting
    # ImportError fits exceptional condition and is suitably descriptive.
    module = import_module(options['module'])
    import pdb
    pdb.set_trace()

    # Attempt to request all necessary models/data from the module.
    # If not complete data set, raise exception.
    # Check for transformer. Output found or not found.

    # language check, company, service, document, documentslanguages

    # Attempt to load al data within a single transaction.
        # Register module and its transformer.
        # Make sure to respect --disabled choice.
        # If storage error, roll back transaction and raise exception.


