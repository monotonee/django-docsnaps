"""
Tests the "install" subcommand's model/data loader.

TransactionTestCase is used for table truncation. AUTO_INCREMENT values are
reset by a truncation, allowing for explicit model PK values and easier
QuerySet comparison.

If TransactionTestCase is evidenced to be too slow, a different solution will
have to be explored. Manual ALTER TABLE statements could be used to reset
AUTO_INCREMENT values, for instance.

Because this test case class reset the database to a known state before
each test, the all() QuerySet method is used. There is no need to filter
results because there will be no other records in the database.

"""

import io
import types
import unittest.mock

import django.db
import django.core.management.base
import django.test

from django_docsnaps.management.commands._install import Command
import django_docsnaps.management.commands._utils as command_utils
import django_docsnaps.models
from .. import utils as test_utils


class ExceptionAttributeMock(unittest.mock.NonCallableMock):
    """
    A class to allow side effects in mock attribute access.

    Designed for a specific test of the transaction rollbacks as a result of
    raised exceptions.

    I may have missed it in the documentation or not yet discovered the
    canonical way to do it, but it appears that side effects cannot be related
    to unittest.mock attrbute access operations. I don't want to mess with
    magic methods so this local class will do for now.

    """

    @property
    def url(self):
        raise django.db.Error


class TestModuleModelsLoad(django.test.TransactionTestCase):

    def setUp(self):
        """
        Capture stdout output to string buffer instead of allowing it to be
        sent to actual terminal stdout.

        """
        self._command = Command(stdout=io.StringIO(), stderr=io.StringIO())
        self._models = test_utils.get_test_models()
        self._docs_langs = self._models[0]
        self._module = unittest.mock.NonCallableMock(
            spec_set=['__class__', '__name__', 'get_models', 'transform'])
        attributes = {
            '__class__': types.ModuleType,
            '__name__': 'mock.module',
            'get_models.return_value': self._models}
        self._module.configure_mock(**attributes)

    def test_disabled_flag(self):
        """
        Test that docsnaps task is inserted as disabled when flag is passed.

        The disabeld flag value is parsed from command line arguments to the
        Django command.

        """
        self._command._load_models(self._module, disabled=True)
        result_set = django_docsnaps.models.DocumentsLanguages.objects.all()
        self.assertEqual(len(result_set), 1)
        self.assertFalse(result_set[0].is_enabled)

    def test_existing_record_warnings(self):
        """
        Test that warnings are emitted each time record already exists in DB.

        Warnings are also tested in other test cases but if this fails, at least
        one knows exactly where to begin looking for other test failures.

        """
        # Configure the mock module to return two models instead of one.
        duplicate_docslangs = django_docsnaps.models.DocumentsLanguages(
            document_id=self._docs_langs.document_id,
            language_id=self._docs_langs.language_id,
            url='should.be.discarded')
        self._module.get_models.return_value = (
            self._docs_langs, duplicate_docslangs)

        self._command._load_models(self._module)

        self.assertGreater(self._command.stdout.getvalue().count('warning:'), 0)

    def test_idempotent_load(self):
        """
        Test that the data loading is idempotent with same data set.

        When data with identical unique or primary keys are inserted, the values
        of the non-indexed fields of the existing data will NOT be overwritten.

        """
        # Configure the mock module to return two models instead of one.
        self._module.get_models.return_value = (
            self._docs_langs, self._docs_langs)

        self._command._load_models(self._module)
        result_set = django_docsnaps.models.DocumentsLanguages.objects\
            .select_related().all()

        # Verify that the existing data was NOT overwritten.
        self.assertEqual(len(result_set), 1)
        self.assertEqual(result_set.first().url, self._docs_langs.url)
        self.assertListEqual(
            list(command_utils.flatten_model_graph(result_set.first())),
            list(command_utils.flatten_model_graph(self._docs_langs)))
        self.assertTrue(result_set.first().is_enabled)

        # Verify that transform record was inserted.
        # transform_set = models.Transform.objects.select_related().all()
        # self.assertEqual(len(transform_set), 1)
        # self.assertEqual(
            # transform_set.first().document_id, self._docs_langs.document_id)
        # self.assertEqual(transform_set.first().module, self._module.__name__)

    def test_load_successful(self):
        """
        Test a successful and uneventful load.

        """
        self._command._load_models(self._module)
        result_set = django_docsnaps.models.DocumentsLanguages.objects\
            .select_related().all()

        # Verify that all foreign key relationships exist and are correct.
        self.assertEqual(len(result_set), 1)
        self.assertEqual(
            list(command_utils.flatten_model_graph(result_set.first())),
            list(command_utils.flatten_model_graph(self._docs_langs)))
        self.assertTrue(result_set.first().is_enabled)

        # Verify that the Transform record was created correctly.
        # transform = models.Transform.objects.all()
        # self.assertEqual(len(transform), 1)
        # self.assertEqual(
            # transform.first().document_id.document_id,
            # self._docs_langs.document_id.document_id)
        # self.assertEqual(transform.first().module, self._module.__name__)

    def test_reinstall_update(self):
        """
        Test that "reinstalling" the plugin module will update necessary data.

        Reinstalling a module when it returns new model field attribute values
        such as the Documentslanguages.url should cause the URL to be updated
        in the database and should issue at least one warning.

        """
        new_url = 'http://new.url.lru'
        duplicate_docslangs = django_docsnaps.models.DocumentsLanguages(
            document_id=self._docs_langs.document_id,
            language_id=self._docs_langs.language_id,
            url=new_url)
        self._module.get_models.return_value = (
            self._docs_langs, duplicate_docslangs)
        self._command._load_models(self._module)

        result_set = django_docsnaps.models.DocumentsLanguages.objects\
            .select_related().all()

        self.assertEqual(len(result_set), 1)
        self.assertEqual(result_set[0].url, new_url)
        self.assertGreater(self._command.stdout.getvalue().count('warning:'), 0)

    def test_transaction_rollback(self):
        """
        Test that the entire load is rolled back on any exception.

        Test this with multiple DocumentsLanguages instances returned from the
        module, with the last one raising an exception. All successfully-
        inserted data should also be rolled back.

        """
        # Configure the mock module to return two models instead of one.
        # The first model will be successful, the second will raise exception.
        exception_docslangs = ExceptionAttributeMock(
            spec_set=django_docsnaps.models.DocumentsLanguages)
        attributes = {
            'document_id': self._docs_langs.document_id,
            'language_id': self._docs_langs.language_id
        }
        exception_docslangs.configure_mock(**attributes)
        self._module.get_models.return_value = (
            self._docs_langs, exception_docslangs)

        # Verify that the proper exception is re-raised.
        with self.assertRaises(django.core.management.base.CommandError):
            self._command._load_models(self._module)

        # Verify that the transaction was rolled back.
        result_set = django_docsnaps.models.DocumentsLanguages.objects\
            .select_related().all()
        self.assertEqual(len(result_set), 0)
