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

import django.core.exceptions
import django.db
from django.core.management.base import BaseCommand, CommandError
from django.db.models.fields.related import ForeignKey

from docsnaps import models
from docsnaps.management.commands._utils import flatten_model_graph


class Command(BaseCommand):

    help = 'Installs a new snapshot job and registers its transforms.'

    def _import_module(self, module_name):
        """
        Attempt to load the module passed as an argument to the subcommand.

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

    def _load_models(self, module, disabled=False):
        """
        Load the module's data.

        All of the module's data is loaded in a transaction.

        Only one exception can be a thread at a given time. Defer raising
        CommandError until after exiting try:except block.

        Args:
            module: The imported plugin module as returned by importlib.
            disabled (bool): The value of the subcommand's "disabled" flag.

        Raises:
            django.core.management.base.CommandError If loading fails.

        """
        self.stdout.write('Attempting to load module data: ', ending='')
        command_error_message = None
        try:
            with django.db.transaction.atomic():
                for model in module.get_models():
                    model_loader = ModelLoader(
                        model,
                        module.__name__,
                        disabled=disabled)
        except django.core.exceptions.MultipleObjectsReturned:
            command_error_message = (
                'Multiple identical records returned for this module\'s data.'
                'This indicates a data integrity violations in the database.')
        except django.db.Error as exception:
            command_error_message = (
                'A database error occurred: ' + str(exception))

        if command_error_message:
                self._raise_command_error(command_error_message)

        self.stdout.write(self.style.SUCCESS('success'))
        for warning in model_loader.warnings:
            self.stdout.write(self.style.WARNING('warning: ') + warning)

    def _raise_command_error(self, message):
        """
        Raise a CommandError and writes a failure string to stdout.

        Within this command class, the pattern of raising the CommandError and
        finishing a stdout string with a failure message is repeated
        consistently. Thus, this method.

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
        Check module interface of imported module.

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
        DocumentsLanguages instances, the relationship fields of which will be
        traversed.

        The goal in validating the models is not to attempt to circumvent
        Pythonic duck typing, but to generate helpful error messages for plugin
        developers.

        It is best to call this after validating module interface in order to
        avoid potential AttributeErrors.

        Args:
            module: The imported plugin module as returned by importlib.

        Raises:
            django.core.management.base.CommandError: With descriptive messages
                iff module is invalid.

        """
        self.stdout.write('Validating module models: ', ending='')

        module_models = module.get_models()

        # Ensure returned models value is not empty.
        if not module_models:
            self._raise_command_error(
                module.__name__ + '.get_models() returned an empty iterable.')

        # Ensure returned models value is an iterable.
        try:
            iter(module_models)
        except TypeError as type_error:
            self._raise_command_error(type_error)

        # Ensure returned models value is an iterable of correct types and
        # minimum necessary model relationship trees are provided.
        required_classes = {
            models.Company,
            models.Service,
            models.Document,
            models.Language,
            models.DocumentsLanguages}
        for model in module_models:
            if isinstance(model, models.DocumentsLanguages):
                returned_classes = set(
                    [m.__class__ for m in flatten_model_graph(model)])
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
            action='store_true',
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
        self._load_models(module, options['disabled'])


        # import pdb
        # pdb.set_trace()

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
    for and, if exceptions are raised, they are allowed to bubble.

    Loading attempted upon instance initialization. The entire loading operation
    is an atomic operation. Either all models are loaded or none are.

    This class is designed for use within the context of this module. All plugin
    module validation is assumed to have been done prior to the instantiation of
    this class.

    Attributes:
        load_successful (boolean): Set to true when or if load completes.
                False otherwise.
        warnings (sequence): A sequence of warning strings suitable for stdout.

    """

    def __init__(self, model, module_name: str, disabled=False):
        """
        Initialize an instance.

        Args:
            module (module): A module object as returned by importlib. The
                module from which the model was returned. The module name is
                used to populate database records.
            model (docsnaps.models.DocumentsLanguages)
            disabled (boolean): If set to True, disables the new job on insert.
                If false, value

        """
        self._disabled = disabled
        self._model = model
        self._module_name = module_name
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
                + str(getattr(existing_model, field_name)) + '". ')
            warning += (
                'Discarded "' + field_name + '" value: "'
                + str(getattr(new_model, field_name)) + '".')

        return warning

    def _load(self):
        """
        Attempt to load a model relationship tree into database.

        If a record already exists in the database for a given entity, then
        the record is left unchanged and is not updated. This makes the load
        operation repeatable with no side effects. A warning is issued if the
        existing record's non-key attributes differ from the incoming record.
        This behavior is designed to guard against multiple modules that may use
        the same data such as two separate Netflix modules.

        That behavior does, however, make module updates a problem. A flag to
        the install command could be passed to force override or a separate
        "update" command could be created.

        I opted to write this explicitly. The method becomes longer, less
        elegant, and possibly more time-consuming to maintain with model changes
        but is easier to read and debug. I'll observe the future consequences of
        this choice.

        To make this dynamic and more immune to model changes, this operation
        would be converted into a relationship graph traversal algorithm that
        automatically distinguishes non-key model fields and can determine the
        type of model class to instantiate for the new record by the class of
        the passed model.

        This method does NOT catch exceptions. Exceptions bubble to next stack
        frame. Transaction start and handling is left to external calling code.

        New models are created for the insert operation so that, if a record
        already exists, the inbound and existing data can be compared.

        See:
            https://docs.djangoproject.com/en/dev/ref/models/querysets/#get-or-create

        """
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
                'is_enabled': self._disabled})
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
            module=self._module_name)
        if not created:
            self.warnings.append(
                transform.__class__.__name__ + ': '
                'Module ' + self._module_name + ' already registered '
                'transform for ' + str(document) + '.')

        self.load_successful = True











