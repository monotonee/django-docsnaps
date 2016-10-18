"""
This module defines tests for the "install" subcommand's _import_module method.

"""

import io
import types

from django.core.management.base import CommandError
from django.test import SimpleTestCase

from docsnaps.management.commands._install import Command


class TestImportModule(SimpleTestCase):

    def setUp(self):
        self._command = Command(stdout=io.StringIO(), stderr=io.StringIO())

    def test_module_load_failure(self):
        """
        Module fails to be imported.

        """
        self.assertRaises(CommandError, self._command._import_module, 'dodge.this')

    def test_module_load_successful2(self):
        """
        Module is imported successfully.

        """
        module = self._command._import_module('bisect')

        self.assertIsInstance(module, types.ModuleType)

