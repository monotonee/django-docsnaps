"""
A Django admin command that will install a new snapshot job.

Before attempting to load the plugin module's data into the database, validation
is performed on the module. This is done to ease plugin module development by
providing helpful and explicit error messages. However, I'm not sure the benefit
is worth the cost in maintenance. If these validation methods prove to inhibit
module API changes or prove to be too brittle, then they will be removed.

All necessary data for the new job is loaded into the database.

"""
from collections import deque
from importlib import import_module

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db.models.fields.related import ForeignKey

import docsnaps.models


class Command(BaseCommand):

    help = 'Installs a new snapshot job and registers its transforms.'

    def _get_relation_tree(self, model):
        """
        A generator method that recursively yields model instances.

        The chain of relationship fields in a model form a tree structure.
        The plugin modules' get_models() function returns an iterable of what
        equates to the deepest nodes in their respective "trees." This method
        yields each model in the relationship trees in a depth-first manner.

        For instance, the DocumentsLanguages models have two relationship
        (ForeignKey) fields: a Document and a Language. This generator will
        first yield the DocumentsLanguages instance before yielding the "child"
        Document and Language instances.

        Since this method yields depth first, it tests for instances of
        relationship fields, not reverse relationship fields.

        Args:
            model (docsnaps.models.DocumentsLanguages): A "child"
                model instance, the relationship fields of which will be
                traversed up the tree.

        Yields:
            docsnaps.models.*: Each model instance of each relationship field
                in the model tree, depth-first.

        See:
            https://github.com/django/django/blob/master/django/db/models/fields/related.py
            https://github.com/django/django/blob/master/django/db/models/fields/reverse_related.py

        """
        model_queue = deque([model])
        while model_queue:
            current_model = model_queue.popleft()
            for field in current_model._meta.get_fields():
                if (isinstance(field, ForeignKey)
                    and hasattr(current_model, field.name)):
                    model_queue.append(getattr(current_model, field.name))
            yield current_model

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

        Checks for the full model relationship tree, from Company to
        DocumentsLanguages. The plugin module must provide an iterable of
        DocumentsLanguages instances the relationship fields of which will be
        traversed.

        The goal in validating the module is not to attempt to circumvent
        Pythonic duck typing, but to generate helpful error messages for plugin
        developers.

        It is best to call this after validating module interface in order to
        avoid AttributeErrors.

        Args:
            module: The imported plugin module as returned by importlib.

        Raises:
            django.core.management.base.CommandError: With descriptive messages
                iff module is invalid.

        """
        self.stdout.write('Validating module models: ', ending='')

        module_models = module.get_models()

        # Return value is an iterable.
        try:
            iter(module_models)
        except TypeError as type_error:
            self._raise_command_error(type_error)

        # Return value is not empty.
        if not module_models:
            self._raise_command_error(
                module.__name__ + '.get_models() returned an empty iterable.')

        # Return value is an iterable of correct types and full model
        # relationship trees are provided.
        required_classes = {
            docsnaps.models.Company,
            docsnaps.models.Service,
            docsnaps.models.Document,
            docsnaps.models.Language,
            docsnaps.models.DocumentsLanguages}
        for model in module_models:
            if isinstance(model, docsnaps.models.DocumentsLanguages):
                returned_classes = set([m.__class__ for m \
                    in self._get_relation_tree(model)])
                diff = required_classes.difference(returned_classes)
                if diff:
                    self._raise_command_error(
                        module.__name__ + '.get_models() returned instance ' +
                        str(model) + ', the model relationships under which '
                        'are missing at least one instance of the following '
                        'models: ' + ', '.join(map(str, diff)))
            else:
                self._raise_command_error(
                    module.__name__ + '.get_models() '
                    'returned incorrect type "' + str(type(model)) + '" '
                    'in iterable.')

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












