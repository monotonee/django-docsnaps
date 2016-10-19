"""
Tests for the "install" subcommand's _validate_module_models method.

"""

import io
import types
import unittest.mock as mock

from django.core.management.base import CommandError
from django.test import SimpleTestCase

from docsnaps.management.commands._install import Command
import docsnaps.models as models


class TestValidateModuleModels(SimpleTestCase):

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
        attributes = {
            '__name__': 'mock.module',
            'get_models.return_value': self._get_models()}
        self._module = mock.NonCallableMock(
            spec=['__name__', 'get_models'])

    def test_valid_module(self):
        """
        Test a module with complete and correct interface and return values.

        """
        self._command._validate_module_models(self._module)

        self.assertIn('success', self._command.stdout.getvalue())




