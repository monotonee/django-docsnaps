"""
Tests the "install" subcommand's plugin module models validation.

Regular expressions are compiled to allow for use of the IGNORECASE flag.

"""

import io
import re
import unittest.mock as mock

from django.core.management.base import CommandError
from django.test import SimpleTestCase

from docsnaps.management.commands._install import Command
import docsnaps.models as models
from .. import utils as test_utils


class TestValidateModuleModels(SimpleTestCase):

    def setUp(self):
        self._command = Command(stdout=io.StringIO(), stderr=io.StringIO())
        self._module = mock.NonCallableMock(
            spec=['__name__', 'get_models', 'transform'])
        attributes = {'__name__': 'mock.module'}
        self._module.configure_mock(**attributes)

    def test_missing_models(self):
        """
        Test missing models from the hierarchy.

        Tests the absence of each model one at a time in sub-tests.

        """
        model_names = ['Language', 'Document']
        for model_name in model_names:
            with self.subTest(missing_model=model_name):
                self._module.get_models.return_value = \
                    test_utils.get_test_models(omit=model_name)
                self.assertRaisesRegex(
                    CommandError,
                    re.compile('.*' + model_name + '.*', flags=re.IGNORECASE),
                    self._command._validate_module_models,
                    self._module)

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

    def test_return_value_wrong_type(self):
        """
        Test get_models return value as iterable of incorrect types.

        """
        self._module.get_models.return_value = (42,)

        self.assertRaisesRegex(
            CommandError,
            re.compile(r'.*type.*', flags=re.IGNORECASE),
            self._command._validate_module_models,
            self._module)
        self.assertIn('failed', self._command.stdout.getvalue())

    def test_valid_module(self):
        """
        Test a module with complete and correct interface and return values.

        """
        self._module.get_models.return_value = test_utils.get_test_models()
        self._command._validate_module_models(self._module)

        self.assertIn('success', self._command.stdout.getvalue())
