"""
This module defines tests for the "install" subcommand's _import_module method.

"""

import io
import types

from django.core.management.base import CommandError
from django.test import SimpleTestCase

from docsnaps.management.commands._install import Command


class TestImportModule(SimpleTestCase):
    """
    Tests of the "install" subcommand's plugin module import.

    The plugin module must exist and must be successfully imported before it
    can be used.

    """

    def setUp(self):
        self._command = Command(stdout=io.StringIO(), stderr=io.StringIO())

    def test_module_load_failure(self):
        """
        Test that module import failure raises a CommandError.

        """
        self.assertRaisesRegex(
            CommandError,
            r'^No module .*$',
            self._command._import_module,
            'dodge.this')

    def test_module_load_success(self):
        """
        Test that a module can be imported successfully.

        """
        module = self._command._import_module('bisect')

        self.assertIsInstance(module, types.ModuleType)
        self.assertIn('success', self._command.stdout.getvalue())
