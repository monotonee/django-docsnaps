"""
A Django admin command that will install a new snapshot job.

Before attempting to load the plugin module's data into the database, validation
is performed on the module. This is done to ease plugin module development by
providing helpful and explicit error messages. However, I'm not sure the benefit
is worth the cost in maintenance. If these validation methods prove to inhibit
module API changes or prove to be too brittle, then they will be removed.

All necessary data for the new job is loaded into the database.

"""

from collections import OrderedDict
from importlib import import_module

from django.core.management.base import BaseCommand, CommandError

import docsnaps.models


class Command(BaseCommand):

    help = 'Installs a new snapshot job and registers its transforms.'

    def _import_module(self, module_name):
        """
        Attempts to load the module passed as an argument to the subcommand.

        Args:
            module_name (string): The fully-qualified, absolute name of the
                plugin module.

        Returns:
            module: The module returned by importlib.import_module if successful.

        Raises:
            django.core.management.base.CommandError: If import fails

        """
        self.stdout.write('Attempting to load module: ', ending='')
        try:
            module = import_module(module_name)
        except ImportError as import_error:
            self._raise_command_error(import_error)
        else:
            self.stdout.write(self.style.SUCCESS('success'))
            return module

    def _raise_command_error(self, message):
        """
        Raises a CommandError and writes a failure string to stdout.

        Within this command class, the pattern of raising the CommandError and
        finishing a stdout string with a failure message is repeated
        consistently.

        Args:
            message (string or Exception): The message to pass to the exception
                constructor. Whatever is passed to an Exception constructor
                seems to be implicitly converted to a string. All Exception
                subclasses appear to output their message when converted.

        Raises:
            django.core.management.base.CommandError

        """
        self.stdout.write(self.style.ERROR('failed'))
        raise CommandError(message)

    def _validate_module_interface(self, module):
        """
        Check module interface and validate models provided by imported module.

        The goal in validating the module is not to attempt to circumvent
        Pythonic duck typing, but to generate helpful error messages for plugin
        developers.

        Args:
            module: The imported plugin module as returned by importlib.

        Raises:
            django.core.management.base.CommandError: If module is invalid.

        """
        self.stdout.write('Validating module interface: ', ending='')

        # Check module interface.
        necessary_callables = ['get_models', 'transform']
        error_message = None
        for callable_name in necessary_callables:
            if not hasattr(module, callable_name):
                error_message = (
                    'No attribute "' + callable_name +
                    '" in ' + module.__name__ + '.')
            elif not callable(getattr(module, callable_name)):
                error_message = (
                    callable_name + ' is not callable in ' +
                    module.__name__ + '.')
            if error_message:
                self._raise_command_error(error_message)

        self.stdout.write(self.style.SUCCESS('success'))

    def _validate_module_models(self, module):
        """
        Validate that the module returns complete model hierarchy.

        Checks for the full model hierarchy, from Company to DocumentsLanguages.
        The plugin module must provide an iterable of DocumentsLanguages
        instances the foreign key and many-to-many attributes of which will be
        traversed.

        The goal in validating the module is not to attempt to circumvent
        Pythonic duck typing, but to generate helpful error messages for plugin
        developers.

        It is best to call this after validating module interface in order to
        avoid AttributeErrors.

        Args:
            module: The imported plugin module as returned by importlib.

        Raises:
            django.core.management.base.CommandError: If module is invalid.

        """
        self.stdout.write('Validating module models: ', ending='')

        module_models = module.get_models()

        # Return value is an iterable.
        try:
            iter(module_models)
        except TypeError as type_error:
            self._raise_command_error(type_error)

        # Elements of iterable are present and of correct type. This smells.
        error_format_string = (
            'No {model} instances returned by ' +
            module.__name__ + '.get_models().')
        error_message = error_format_string.format(model='DocumentsLanguages')
        for model in module_models:
            if not isinstance(model, docsnaps.models.DocumentsLanguages):
                error_message = error_format_string.format(
                    model='DocumentsLanguages')
                break
            elif (not hasattr(model, 'language_id') or
                not isinstance(model.language_id, docsnaps.models.Language)):
                error_message = error_format_string.format(model='Language')
                break
            elif (not hasattr(model, 'document_id') or
                not isinstance(model.document_id, docsnaps.models.Document)):
                error_message = error_format_string.format(model='Document')
                break
            elif (not hasattr(model.document_id, 'service_id') or
                not isinstance(
                    model.document_id.service_id,
                    docsnaps.models.Service)):
                error_message = error_format_string.format(model='Service')
                break
            elif (not hasattr(model.document_id.service_id, 'company_id') or
                not isinstance(
                    model.document_id.service_id.company_id,
                    docsnaps.models.Company)):
                error_message = error_format_string.format(model='Company')
                break
            else:
                error_message = None

        # Note: if the iterable returned by the module was empty, then the loop
        # above will not have made an iteration. This raises an exception with
        # the default value of the error message above.
        if error_message:
            self._raise_command_error(error_message)

        self.stdout.write(self.style.SUCCESS('success'))

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
        module = self._import_module(options['module'])
        self._validate_module_interface(module)
        self._validate_module_models(module)


        # import pdb
        # pdb.set_trace()

        # Attempt to request all necessary models/data from the module.
        # If not complete data set, raise exception.
        # Check for transformer. Output found or not found.

        # language check, company, service, document, documentslanguages

        # Attempt to load al data within a single transaction.
            # Remember that the get_or_create() method returns tuples.
            # https://docs.djangoproject.com/en/dev/ref/models/querysets/#get-or-create
            # Register module and its transformer.
            # Make sure to respect --disabled choice.
            # If storage error, roll back transaction and raise exception.












