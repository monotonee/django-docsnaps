"""
Tests the "install" subcommand's plugin module validation.

"""

import io
import unittest.mock

import django.core.management.base
import django.test

from django_docsnaps.management.commands._install import Command


class TestModuleInterfaceValidation(django.test.SimpleTestCase):

    def setUp(self):
        self._command = Command(stdout=io.StringIO(), stderr=io.StringIO())
        self._module = unittest.mock.NonCallableMock()
        self._module.__name__ = 'mock.module'

    def test_get_models_missing(self):
        """
        Test a module that's missing a get_models callable attribute.

        """
        self._module.mock_add_spec(['__name__'], spec_set=True)

        self.assertRaises(
            django.core.management.base.CommandError,
            self._command._validate_module_interface,
            self._module)

    def test_get_models_not_callable(self):
        """"
        Test a module in which get_models attribute is not callable.

        """
        self._module.mock_add_spec(['__name__', 'get_models'], spec_set=True)
        self._module.get_models = unittest.mock.NonCallableMock()

        self.assertRaises(
            django.core.management.base.CommandError,
            self._command._validate_module_interface,
            self._module)

    def test_transform_missing(self):
        """
        Test a module that's missing a transform callable attribute.

        """
        self._module.mock_add_spec(['__name__', 'get_models'], spec_set=True)

        self.assertRaises(
            django.core.management.base.CommandError,
            self._command._validate_module_interface,
            self._module)

    def test_transform_not_callable(self):
        """"
        Test a module in which transform attribute is not callable.

        """
        self._module.mock_add_spec(
            ['__name__', 'get_models', 'transform'],
            spec_set=True)
        self._module.transform = unittest.mock.NonCallableMock()

        self.assertRaises(
            django.core.management.base.CommandError,
            self._command._validate_module_interface,
            self._module)

    def test_valid_module_interface(self):
        """
        Test a module with complete and correct interface.

        """
        self._module.mock_add_spec(
            ['__name__', 'get_models', 'transform'],
            spec_set=True)
        self._command._validate_module_interface(self._module)
