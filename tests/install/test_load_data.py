"""
Tests the "install" subcommand's _load_data method.

"""

import importlib
import io
import unittest.mock as mock

from django.core.management.base import CommandError
from django.test import TestCase

from docsnaps.management.commands._install import Command
import docsnaps.models as models


@mock.patch('docsnaps.management.commands._install.import_module')
class TestValidateModuleInterface(TestCase):
    """
    Successful insert.
        Check transform table
    Warning if field not updated due to existing record.
    Failed insert.
        Roll back transaction.
    Repeatable insert.
        No change
        Raise warning with unupdated fields.

    """
    def _get_models(self):
        """
        Construct a valid model hierarchy with relationship attributes assigned.

        No parts of the data need to be real nor do URLs need to point to real
        resources. This is simply to test database interaction.

        Returns:
            iterable: Iterable of docsnaps.models.DocumentsLanguages instances.
                If DocumentsLanguages were omitted using the optional keyword
                argument, then the iterable will be empty.

        """
        language = models.Language(
            name='English',
            code_iso_639_1='en')
        company = models.Company(
            name='Test, Inc.',
            website='https://test.tset')
        service = models.Service(
            name='Test',
            website='https://test.tset',
            company_id=company)
        document = models.Document(
            name='Terms of Use',
            service_id=service)
        docs_langs = (
            models.DocumentsLanguages(
                document_id=document,
                language_id=language,
                url='help.test.tset/legal/termsofuse?locale=en'),)

        return docs_langs

    def setUp(self):
        self._command = Command(stdout=io.StringIO(), stderr=io.StringIO())
        self._models = self._get_models()
        self._module = mock.NonCallableMock(
            spec=['__name__', 'get_models', 'transform'])
        attributes = {
            '__name__': 'mock.module',
            'get_models.return_value': self._models}
        self._module.configure_mock(**attributes)

    def test_load_successful(self, mock_import_module):
        """
        Test a successful and uneventful load.

        """
        mock_import_module.return_value = self._module
        self._command.handle(module='test.test')

        docs_langs = self._models[0]

        # Does assertQuerysetEqual recurse relationships?
        # docs_langs_qs = models.DocumentsLanguages.objects.filter(
            # document_id=docs_langs.document_id,
            # language_id=docs_langs.language_id)
        # self.assertQuerysetEqual(docs_langs_qs, [repr(docs_langs)])

        test_company = docs_langs.document_id.service_id.company_id
        company_qs = models.Company.objects.filter(
            name=test_company.name)
        self.assertQuerysetEqual(company_qs, [repr(test_company)])


