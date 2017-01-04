"""
Tests the "install" subcommand's model/data loader.

TransactionTestCase is used for table truncation. AUTO_INCREMENT values are
reset by a truncation, allowing for explicit model PK values and easier
QuerySet comparison.

If TransactionTestCase is evidenced to be too slow, a different solution will
have to be explored. Manual ALTER TABLE statements could be used to reset
AUTO_INCREMENT values, for instance.

"""

import io
from types import ModuleType
import unittest.mock as mock

from django.test import TransactionTestCase

from .. import utils as test_utils
from docsnaps.management.commands._install import ModelLoader
import docsnaps.management.commands._utils as command_utils
import docsnaps.models as models


class TestModelLoader(TransactionTestCase):

    def setUp(self):
        self._models = test_utils.get_test_models()
        self._docs_langs = self._models[0]
        self._module = mock.NonCallableMock(
            spec=['__name__', 'get_models', 'transform'])
        attributes = {
            '__class__': ModuleType,
            '__name__': 'mock.module',
            'get_models.return_value': self._models}
        self._module.configure_mock(**attributes)

    def test_load_successful(self):
        """
        Test a successful and uneventful load.

        """
        document = self._docs_langs.document_id
        language = self._docs_langs.language_id

        model_loader = ModelLoader(self._module, self._docs_langs)
        result = models.DocumentsLanguages.objects.select_related().filter(
            document_id=document,
            language_id=language)

        # Manager.get() raises an exception if multiple or no records returned.
        # I'm counting it as an assertion.
        transform = models.Transform.objects.get(
            document_id=document,
            module=self._module.__name__)
        self.assertEqual(len(result), 1)
        self.assertEqual(
            list(command_utils.flatten_model_graph(result.first())),
            list(command_utils.flatten_model_graph(self._docs_langs)))
        self.assertFalse(model_loader.warnings)

    def test_idempotent_load(self):
        """
        Test that the data loading is idempotent with same data set.

        Remember that Manager.get() raises an exception if multiple or no
        records returned. Manager.get() is used to fetch Transform records.
        Their function is essentially that of assertions.

        Because both instances of loading insert the same data, only the warning
        about the duplicate Transform is expected.

        """
        document = self._docs_langs.document_id
        language = self._docs_langs.language_id

        model_loader_1 = ModelLoader(self._module, self._docs_langs)
        result_1 = models.DocumentsLanguages.objects.select_related().filter(
            document_id=document,
            language_id=language)
        result_1_len = len(result_1)
        transform_1 = models.Transform.objects.get(
            document_id=document,
            module=self._module.__name__)

        model_loader_2 = ModelLoader(self._module, self._docs_langs)
        result_2 = models.DocumentsLanguages.objects.select_related().filter(
            document_id=document,
            language_id=language)
        result_2_len = len(result_2)
        transform_2 = models.Transform.objects.get(
            document_id=document,
            module=self._module.__name__)

        # Primarily testing second result set. Testing a single result set is
        # done in previous test. We're only interested in the results of
        # repeated write here.
        self.assertEqual(result_2_len, 1)
        self.assertTrue(model_loader_2.warnings)
        self.assertTrue(
            warning for warning in model_loader_2.warnings
            if transform_2.__class__.__name__ in warning)
        self.assertEqual(
            list(command_utils.flatten_model_graph(result_2.first())),
            list(command_utils.flatten_model_graph(self._docs_langs)))

    def test_argument_validation(self):
        """
        Test that argument type checking raises exceptions correctly.

        """
        raise NotImplementedError('Finish this test.')

    def test_transaction_rollback(self):
        """
        Test that the entire load is rolled back on any exception.

        """
        raise NotImplementedError('Finish this test.')

    def test_existing_record_warnings(self):
        """
        Test that warnings are emitted each time record already exists in DB.

        """
        raise NotImplementedError('Finish this test.')




