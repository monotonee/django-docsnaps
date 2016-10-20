"""
Tests for the "install" subcommand's _validate_module_models method.

"""

import io
import re
import types
import unittest.mock as mock

from django.core.management.base import CommandError
from django.test import SimpleTestCase

from docsnaps.management.commands._install import Command
import docsnaps.models as models


class TestValidateModuleModels(SimpleTestCase):

    def _get_models(self, omit=None):
        """
        Construct a valid model hierarchy with relationship attributes assigned.

        No parts of the data need to be real nor do URLs need to point to real
        resources. This is simply to test valid module structure and values.

        Args:
            omit (string): The name of a model to omit from hierarchy. The value
                in the hierarchy will be set to None. If the omitted model is
                DocumentsLanguages, an iterable of which is normally returned,
                the return value will be an empty iterable.

        Returns:
            iterable: Iterable of docsnaps.models.DocumentsLanguages instances.
                If DocumentsLanguages were omitted using the optional keyword
                argument, then the iterable will be empty.

        Raises:
            ValueError: If value for "omit" argument is provided but the
                specified model name does not exist or is not used inside the
                method.

        """
        model_name = None
        model_dict = {}

        # Assign models
        model_name = 'Language'
        model_dict[model_name] = models.Language(
            name='English',
            code_iso_639_1='en') \
            if omit != model_name else None

        model_name = 'Company'
        model_dict[model_name] = models.Company(
            name='Test, Inc.',
            website='https://test.tset') \
            if omit != model_name else None

        model_name = 'Service'
        model_dict[model_name] = models.Service(
            name='Test',
            website='https://test.tset',
            company_id=model_dict['Company']) \
            if omit != model_name else None

        model_name = 'Document'
        model_dict[model_name] = models.Document(
            name='Terms of Use',
            service_id=model_dict['Service']) \
            if omit != model_name else None

        model_name = 'DocumentsLanguages'
        model_dict[model_name] = (
            models.DocumentsLanguages(
                document_id=model_dict['Document'],
                language_id=model_dict['Language'],
                url='help.test.tset/legal/termsofuse?locale=en'),) \
            if omit != model_name else ()

        # If "omit" argument was passed and yet no models were omitted from the
        # hierarchy, then value of "omit" must not correspond to a model name.
        if (omit and None not in list(model_dict.values()) and
            len(model_dict['DocumentsLanguages']) > 0):
            raise ValueError(
                'Cannot omit model "' + omit + '". No such model exists.')

        return model_dict['DocumentsLanguages']

    def setUp(self):
        self._command = Command(stdout=io.StringIO(), stderr=io.StringIO())
        attributes = {'__name__': 'mock.module'}
        self._module = mock.NonCallableMock(
            spec=['__name__', 'get_models', 'transform'])

    def test_valid_module(self):
        """
        Test a module with complete and correct interface and return values.

        """
        self._module.get_models.return_value = self._get_models()
        self._command._validate_module_models(self._module)

        self.assertIn('success', self._command.stdout.getvalue())

    def test_return_value_not_iterable(self):
        """
        Test the module's get_models return value as a non-iterable.

        """
        self._module.get_models.return_value = 42

        self.assertRaisesRegex(
            CommandError,
            re.compile(r'.*not iterable.*', flags=re.IGNORECASE),
            self._command._validate_module_models,
            self._module)
        self.assertIn('failed', self._command.stdout.getvalue())

    def test_missing_models(self):
        """
        Test missing models from the hierarchy.

        Tests the absence of each model, one at a time.

        """
        model_names = [
            'Language',
            'Company',
            'Service',
            'Document',
            'DocumentsLanguages']
        for model_name in model_names:
            with self.subTest(missing_model=model_name):
                self._module.get_models.return_value = self._get_models(
                    omit=model_name)
                self.assertRaisesRegex(
                    CommandError,
                    re.compile('.*"' + model_name + '".*', flags=re.IGNORECASE),
                    self._command._validate_module_models,
                    self._module)
                self.assertIn('failed', self._command.stdout.getvalue())
