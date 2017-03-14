"""
A Django admin command that will install a new snapshot job.

All necessary data for the new job is loaded into the database.

Before attempting to load the plugin module's data into the database, validation
is performed on the module. This is done to ease plugin module development by
providing helpful and explicit error messages. However, I'm not sure the benefit
is worth the cost in maintenance. If these validation methods prove to inhibit
module API changes or prove to be too brittle, then they will be removed.

Note that exceptions are caught in each private method instead of using a single
try-except block in the handle() method. This is done to allow more specificity
of exception classes in the except clause. Due to the wide array of operations
occurring under the handle() method, the set of possible exception classes
becomes too large and increases the risk of catching an exception that should
be allowed to bubble.

"""
import importlib

import django.core.exceptions
import django.db
import django.core.management.base

import django_docsnaps.management.commands._utils as command_utils
import django_docsnaps.models


class Command(django.core.management.base.BaseCommand):

    help = 'Installs a new snapshot job and registers its transforms.'

    def _import_module(self, module_name):
        """
        Attempt to load the module passed as an argument to the subcommand.

        Args:
            module_name (string): The fully-qualified, absolute name of the
                plugin module.

        Returns:
            module: The module returned by importlib.import_module if
                successful.

        Raises:
            django.core.management.base.CommandError: If import fails.

        """
        self.stdout.write('Attempting to load module: ', ending='')
        try:
            module = importlib.import_module(module_name)
        except ImportError as import_error:
            command_utils.raise_command_error(self.stdout, import_error)
        else:
            self.stdout.write(self.style.SUCCESS('success'))
            return module

    def _load_models(self, module, disabled=False):
        """
        Load the module's data.

        All of the module's data is loaded in a transaction.

        Only one exception can be in a thread at a given time. Defer raising
        django.core.management.base.CommandError until after exiting try:except
        block.

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
                        disabled=disabled)
        except django.core.exceptions.MultipleObjectsReturned:
            command_error_message = (
                'Multiple identical records returned for this module\'s data.'
                'This indicates a data integrity violation in the database.')
        except django.db.Error as exception:
            command_error_message = (
                'A database error occurred: ' + str(exception))

        if command_error_message:
            command_utils.raise_command_error(
                self.stdout,
                command_error_message)

        self.stdout.write(self.style.SUCCESS('success'))
        for warning in model_loader.warnings:
            self.stdout.write(self.style.WARNING('warning: ') + warning)

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

        necessary_callables = ['get_models', 'transform']
        error_message = None
        for callable_name in necessary_callables:
            if not hasattr(module, callable_name):
                error_message = 'No attribute "{!s}" in {!s}.'
            elif not callable(getattr(module, callable_name)):
                error_message = '"{!s}" is not callable in {!s}.'
            if error_message:
                error_message = error_message.format(
                    callable_name,
                    module.__name__)
                command_utils.raise_command_error(self.stdout, error_message)

        self.stdout.write(self.style.SUCCESS('success'))

    def _validate_module_models(self, module):
        """
        Validate that the module returns complete model hierarchy.

        Checks for the full model relationship tree. The plugin module must
        provide an iterable of DocumentsLanguages instances, the relationship
        fields of which will be traversed.

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
            command_utils.raise_command_error(
                self.stdout,
                module.__name__ + '.get_models() returned an empty iterable.')

        # Ensure returned models value is an iterable.
        try:
            iter(module_models)
        except TypeError as type_error:
            command_utils.raise_command_error(self.stdout, type_error)

        # Ensure returned models value is an iterable of correct types and
        # minimum necessary model relationship trees are provided.
        # Consider using set.symmetric_difference().
        # https://docs.python.org/3/library/stdtypes.html#set.symmetric_difference
        required_classes = {
            django_docsnaps.models.Document,
            django_docsnaps.models.Language,
            django_docsnaps.models.DocumentsLanguages}
        for model in module_models:
            if isinstance(model, django_docsnaps.models.DocumentsLanguages):
                returned_classes = set(
                    [m.__class__ for m in command_utils.flatten_model_graph(
                        model)])
                diff = required_classes.difference(returned_classes)
                if diff:
                    command_utils.raise_command_error(
                        self.stdout,
                        module.__name__ + '.get_models() returned instance ' +
                        str(model) + ', the model relationships under which '
                        'are missing at least one instance of the following '
                        'models: ' + ', '.join(map(str, diff)))
            else:
                command_utils.raise_command_error(
                    self.stdout,
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


class ModelLoader:
    """
    A helper class that handles loading of models provided by a plugin module.

    Given a DocumentsLanguages instance, its relationship tree is traversed and
    new models are inserted. Edge cases and exceptional conditions are accounted
    for and, if exceptions are raised, they are allowed to bubble.

    Loading attempted upon instance initialization. Transactional atomicity is
    up to the calling context.

    This class is designed for use within the context of this module. All plugin
    module validation is assumed to have been done prior to the instantiation of
    this class.

    Attributes:
        load_successful (boolean): Set to true when or if load completes.
                False otherwise.
        warnings (sequence): A sequence of warning strings suitable for stdout.

    """

    def __init__(self, model, disabled=False):
        """
        Initialize an instance.

        Args:
            model (django_docsnaps.models.DocumentsLanguages): The root of the
                model relationship graph.
            disabled (boolean): If set to True, disables the new job on insert.
                If false, value

        """
        self._disabled = disabled
        self._model = model

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
            existing_model (django_docsnaps.models.*): A model instance of the
                existing record. Must be instance of same model as new_model.
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
        # Document
        new_document = self._model.document_id
        document, created = django_docsnaps.models.Document.objects\
            .get_or_create(
                module=new_document.module,
                name=new_document.name)
        if not created:
            warning = 'Document "{!s}" for module {!s} already exists.'
            warning = warning.format(new_document.name, new_document.module)
            self.warnings.append(warning)

        # Language
        new_language = self._model.language_id
        language, created = django_docsnaps.models.Language.objects\
            .get_or_create(
                code_iso_639_1=new_language.code_iso_639_1,
                defaults={'name': new_language.name})
        if not created:
            warning = (
                'Language with 639-1 ISO code "{!s}" already exists. '
                'New record not inserted.')
            warning = warning.format(new_language.code_iso_639_1)
            if new_language.name.lower() != language.name.lower():
                name_warning = (
                    'Additionally, existing record has name "{!s}" while the '
                    'new record had name "{!s}".')
                name_warning = name_warning.format(
                    language.code_iso_639_1, new_language.code_iso_639_1)
                warning = ' '.join([warning, name_warning])
            self.warnings.append(warning)

        # DocumentsLanguages
        # Updates URL if different.
        is_enabled = self._disabled == False
        new_docs_langs = self._model
        docs_langs, created = django_docsnaps.models.DocumentsLanguages.objects\
            .get_or_create(
                document_id=document,
                language_id=language,
                defaults={
                    'url': new_docs_langs.url,
                    'is_enabled': is_enabled})
        # If this block is entered, Document warning has already been issued.
        if not created and new_docs_langs.url != docs_langs.url:
            old_url = docs_langs.url
            docs_langs.url = new_docs_langs.url
            docs_langs.save()
            warning = (
                'Updated document instance URL. Old URL was: "{!s}". '
                'New URL is: "{!s}".')
            warning = warning.format(old_url, new_docs_langs.url)
            self.warnings.append(warning)

        # Transform
        # transform, created = django_docsnaps.models.Transform.objects\
            # .get_or_create(
                # document_id=document,
                # module=self._module_name)
        # if not created:
            # self.warnings.append(
                # transform.__class__.__name__ + ': '
                # 'Module ' + self._module_name + ' already registered '
                # 'transform for ' + str(document) + '.')

        self.load_successful = True











