"""
Tests for the "install" subcommand's _validate_module method.

"""

import io
import types
import unittest.mock as mock

from django.core.management.base import CommandError
from django.test import SimpleTestCase

from docsnaps.management.commands._install import Command
import docsnaps.models as models


class TestValidateModule(SimpleTestCase):

    def _get_models(self):
        """
        Construct a valid model hierarchy with relationship attributes assigned.

        No parts of the data need to be real nor do URLs need to point to real
        resources. This is simply to test valid module structure and values.

        Returns:
            iterable: Iterable of docsnaps.models.DocumentsLanguages instances.

        """
        lang_en = models.Language(name='English', code_iso_639_1='en')
        company = models.Company(
            name='Test, Inc.',
            website='https://test.tset')
        service = models.Service(
            name='Test',
            website='https://test.tset',
            company_id=company)
        document = models.Document(name='Terms of Use', service_id=service)
        documents_languages = (
            models.DocumentsLanguages(
                document_id=document,
                language_id=lang_en,
                url='help.test.tset/legal/termsofuse?locale=en'))

        return documents_languages

    def setUp(self):
        self._command = Command(stdout=io.StringIO(), stderr=io.StringIO())
        self._module = mock.NonCallableMock()

    def test_valid_module(self):
        """
        Test a module with complete and correct interface and return values.

        """
        attributes = {
            'get_models.return_value': self._get_models(),
            'transform.side_effect': lambda x: x}
        self._module.configure_mock(**attributes)
        self._command._validate_module(self._module)

        self.assertIn('success', self._command.stdout.getvalue())

    def test_get_models_missing(self):
        """
        Test a module that's missing a get_module callable attribute.

        """
        self._module.mock_add_spec(['__name__'], spec_set=True)
        self._module.__name__ = 'mock.module'

        self.assertRaisesRegex(
            CommandError,
            r'^No attribute "get_models" .*$',
            self._command._validate_module,
            self._module)
        self.assertIn('failed', self._command.stdout.getvalue())

    def test_get_models_not_callable(self):
        """"
        Test a module in which get_models attribute is not callable.

        """
        self._module.mock_add_spec(['__name__', 'get_models'], spec_set=True)
        self._module.__name__ = 'mock.module'
        self._module.get_models = mock.NonCallableMock()

        self.assertRaisesRegex(
            CommandError,
            r'^get_models is not callable .*$',
            self._command._validate_module,
            self._module)
        self.assertIn('failed', self._command.stdout.getvalue())

    def test_transform_missing(self):
        """
        Test a module that's missing a transform callable attribute.

        """
        self._module.mock_add_spec(['__name__', 'get_models'], spec_set=True)
        self._module.__name__ = 'mock.module'

        self.assertRaisesRegex(
            CommandError,
            r'^No attribute "transform" .*$',
            self._command._validate_module,
            self._module)
        self.assertIn('failed', self._command.stdout.getvalue())

    def test_transform_not_callable(self):
        """"
        Test a module in which transform attribute is not callable.

        """
        self._module.mock_add_spec(
            ['__name__', 'get_models', 'transform'],
            spec_set=True)
        self._module.__name__ = 'mock.module'
        self._module.transform = mock.NonCallableMock()

        self.assertRaisesRegex(
            CommandError,
            r'^transform is not callable .*$',
            self._command._validate_module,
            self._module)
        self.assertIn('failed', self._command.stdout.getvalue())


