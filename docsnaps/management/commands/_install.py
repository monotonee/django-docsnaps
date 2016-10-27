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
from types import ModuleType

from django.core.exceptions import MultipleObjectsReturned
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models.fields.related import ForeignKey

from docsnaps import models


class Command(BaseCommand):

    help = 'Installs a new snapshot job and registers its transforms.'

    def _get_relation_tree(self, model):
        """
        Recursively yield related model instances.

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
            model (models.DocumentsLanguages): A "child"
                model instance, the relationship fields of which will be
                traversed up the tree.

        Yields:
            models.*: Each model instance of each relationship field
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

    def _load_models(self, module):
        self.stdout.write('Loading module data: ', ending='')

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
            models.Company,
            models.Service,
            models.Document,
            models.Language,
            models.DocumentsLanguages}
        for model in module_models:
            if isinstance(model, models.DocumentsLanguages):
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
        self._load_models(module)


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


class ModelLoader:
    """
    A helper class that handles loading of models provided by a plugin module.

    Given a DocumentsLanguages instance, its relationship tree is traversed and
    new models are inserted. Edge cases and exceptional conditions are accounted
    for and, if exceptions are raised, they are allowed to bubble to next stack
    frame.

    Loading attempted upon instance initialization. The entire loading operation
    is an atomic operation. Either all models are loaded or none are.

    This class is designed for use within the context of this module. No
    constructor argument checking is performed. All plugin module validation is
    assumed to have been done prior to the calling of this class.

    Attributes:
        warnings (sequence): A sequence of warning strings suitable for stdout.

    """

    def __init__(self, module, model):
        """
        Initialize model.

        Attributes:
            load_successful (boolean): Set to true when or if load completes.
                False otherwise.
            warnings (sequence): A sequence of strings, each containing a
                warning intended for output to stdout.

        Args:
            module (module): A module object as returned by importlib.
            model (docsnaps.models.DocumentsLanguages)

        Raises:
            ValueError: If model argument is instance of incorrect model.

        """
        if not isinstance(module, ModuleType):
            raise ValueError(
                'Passed module must be ModuleType instance.')
        if not isinstance(model, models.DocumentsLanguages):
            raise ValueError(
                'Passed model must be DocumentsLanguages instance.')

        self._model = model
        self._module = module
        self.load_successful = False
        self.warnings = []

        self._load()

    def _generate_warning(self, existing_model, new_model, field_names):
        """
        Create a warning string.

        Creates warning strings to provide output from the loading process. A
        warning is output when a model already exists in the database with
        one or more different non-key field values.

        Both arguments should be the same model type.

        Args:
            existing_model (docsnaps.models.*): A model instance of the existing
                record. Must be instance of same model as new_model.
            new_model (docsnaps.models.*): A model instance of the new record.
                Must be instance of same model as existing_model.
            field_names (iterable): The names of the fields the values of which
                are different between the two models.

        Returns:
            string: A string to be written to stdout.

        """
        warning = (
            'Existing ' + str(existing_model) + ' found with different field '
            'values. Existing record will not be updated. ')
        for field_name in field_names:
            warning += (
                'Existing "' + field_name + '" value: "'
                + str(getattr(existing_model, field_name)) + '".')
            warning += (
                'Discarded "' + field_name + '" value: "'
                + str(getattr(new_model, field_name)) + '".')

        return warning

    def _load(self):
        """
        Attempt to load a model relationship tree into database.

        If a record already exists in the database for a given entity, then
        the record is left unchanged and is not updated. This makes the load
        operation repeatable with no side effects.

        I opted to write this explicitly. The method becomes longer and less
        elegant but is easier to read and debug.

        This method does NOT catch exceptions. Exceptions bubble to next stack
        frame, first passing through the atomic context and rolling back the
        transaction.

        """
        with transaction.atomic():

            # Company
            new_company = self._model.document_id.service_id.company_id
            company, created = models.Company.objects.get_or_create(
                name=new_company.name,
                defaults={'website': new_company.website})
            if new_company.website != company.website:
                self.warnings.append(
                    self._generate_warning(company, new_company, ['website']))

            # Service
            new_service = self._model.document_id.service_id
            service, created = models.Service.objects.get_or_create(
                name=new_service.name,
                company_id=company,
                defaults={'website': new_service.website})
            if new_service.website != service.website:
                self.warnings.append(
                    self._generate_warning(service, new_service, ['website']))

            # Document
            new_document = self._model.document_id
            document, created = models.Document.objects.get_or_create(
                name=new_document.name,
                service_id=service)

            # Language
            new_language = self._model.language_id
            language, created = models.Language.objects.get_or_create(
                code_iso_639_1=new_language.code_iso_639_1,
                defaults={'name': new_language.name})
            if new_language.name != language.name:
                self.warnings.append(
                    self._generate_warning(language, new_language, ['name']))

            # DocumentsLanguages
            new_docs_langs = self._model
            docs_langs, created = models.DocumentsLanguages.objects.get_or_create(
                document_id=document,
                language_id=language,
                defaults={
                    'url': new_docs_langs.url,
                    'is_enabled': new_docs_langs.is_enabled})
            differing_fields = []
            if new_docs_langs.url != docs_langs.url:
                differing_fields.append('url')
            elif new_docs_langs.is_enabled != docs_langs.is_enabled:
                differing_fields.append('is_enabled')
            if differing_fields:
                self.warnings.append(
                    self._generate_warning(
                        docs_langs,
                        new_docs_langs,
                        differing_fields))

            # Transform
            transform, created = models.Transform.objects.get_or_create(
                document_id=document,
                module=self._module.__name__)
            if not created:
                self.warnings.append(
                    transform.__class__.__name__ + ': '
                    'Module ' + self._module.__name__ + ' already registered '
                    'transform for ' + str(document) + '.')

            self.load_successful = True











