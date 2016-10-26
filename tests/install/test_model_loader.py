"""
Tests the "install" subcommand's model/data loader.

"""

import importlib
import io
from types import ModuleType
import unittest.mock as mock

from django.core.management.base import CommandError
from django.test import TestCase

from .. import utils as test_utils
from docsnaps.management.commands._install import ModelLoader
import docsnaps.management.commands._utils as command_utils
import docsnaps.models as models


class TestModelLoader(TestCase):

    def setUp(self):
        self._models = test_utils.get_test_models()
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
        docs_langs = self._models[0]
        model_loader = ModelLoader(self._module, docs_langs)
        result = models.DocumentsLanguages.objects.filter(
            document_id=docs_langs.document_id,
            language_id=docs_langs.language_id).select_related()

        # Manager.get() raises an exception if multiple or no records returned.
        # I'm counting it as an assertion.
        transform = models.Transform.objects.get(
            document_id=docs_langs.document_id,
            module=self._module.__name__)
        self.assertEqual(len(result), 1)
        self.assertEqual(
            list(command_utils.flatten_model_graph(result.first())),
            list(command_utils.flatten_model_graph(docs_langs)))
        self.assertFalse(model_loader.warnings)

    def test_idempotent_load(self):
        """
        Test that the data loading is idempotent with same data set.

        """
        raise NotImplementedError('Finish this test.')

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




