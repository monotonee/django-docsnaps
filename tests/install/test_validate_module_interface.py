"""
Tests for the "install" subcommand's _validate_module_interface method.

"""

import io
import types
import unittest.mock as mock

from django.core.management.base import CommandError
from django.test import SimpleTestCase

from docsnaps.management.commands._install import Command
import docsnaps.models as models


class TestValidateModuleInterface(SimpleTestCase):

    def setUp(self):
        self._command = Command(stdout=io.StringIO(), stderr=io.StringIO())
        self._module = mock.NonCallableMock()
        self._module.__name__ = 'mock.module'

    def test_valid_module_interface(self):
        """
        Test a module with complete and correct interface.

        """
        self._module.mock_add_spec(
            ['__name__', 'get_models', 'transform'],
            spec_set=True)
        self._command._validate_module_interface(self._module)

        self.assertIn('success', self._command.stdout.getvalue())

    def test_get_models_missing(self):
        """
        Test a module that's missing a get_module callable attribute.

        """
        self._module.mock_add_spec(['__name__'], spec_set=True)

        self.assertRaisesRegex(
            CommandError,
            r'^No attribute "get_models" .*$',
            self._command._validate_module_interface,
            self._module)
        self.assertIn('failed', self._command.stdout.getvalue())

    def test_get_models_not_callable(self):
        """"
        Test a module in which get_models attribute is not callable.

        """
        self._module.mock_add_spec(['__name__', 'get_models'], spec_set=True)
        self._module.get_models = mock.NonCallableMock()

        self.assertRaisesRegex(
            CommandError,
            r'^get_models is not callable .*$',
            self._command._validate_module_interface,
            self._module)
        self.assertIn('failed', self._command.stdout.getvalue())

    def test_transform_missing(self):
        """
        Test a module that's missing a transform callable attribute.

        """
        self._module.mock_add_spec(['__name__', 'get_models'], spec_set=True)

        self.assertRaisesRegex(
            CommandError,
            r'^No attribute "transform" .*$',
            self._command._validate_module_interface,
            self._module)
        self.assertIn('failed', self._command.stdout.getvalue())

    def test_transform_not_callable(self):
        """"
        Test a module in which transform attribute is not callable.

        """
        self._module.mock_add_spec(
            ['__name__', 'get_models', 'transform'],
            spec_set=True)
        self._module.transform = mock.NonCallableMock()

        self.assertRaisesRegex(
            CommandError,
            r'^transform is not callable .*$',
            self._command._validate_module_interface,
            self._module)
        self.assertIn('failed', self._command.stdout.getvalue())
