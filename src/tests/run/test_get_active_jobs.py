"""
Tests the selection of job data from the database.

"""

import datetime
import io
import unittest.mock as mock

import django.core.management.base
import django.db
from django.test import TestCase

from .. import utils as test_utils
from docsnaps.management.commands._run import Command
import docsnaps.management.commands._utils as command_utils
import docsnaps.models


class TestGetActiveJobs(TestCase):

    def setUp(self):
        """
        Capture stdout output to string buffer instead of allowing it to be
        sent to actual terminal stdout.

        """
        self._command = Command(stdout=io.StringIO(), stderr=io.StringIO())

    @classmethod
    def setUpTestData(self):
        """
        Load baseline data for the tests.

        Might switch to fixtures in the future.

        See:
            https://docs.djangoproject.com/en/dev/topics/testing/tools/#fixture-loading

        """
        document = None
        documents_languages = test_utils.get_test_models()[0]
        snapshot_timedelta = datetime.timedelta(days=1)
        snapshot_datetime = datetime.datetime.today() - snapshot_timedelta

        # Insert base models with a single active job.
        # Save a reference to the Document instance for later use.
        test_models = command_utils.flatten_model_graph(documents_languages)
        for model in reversed(list(test_models)):
            if isinstance(model, docsnaps.models.Document):
                document = model
            model.save()

        # Create Transform records.
        # Two transform records with sequential priority.
        docsnaps.models.Transform.objects.create(
            document_id=document,
            module='fake.module1',
            execution_priority=0)
        docsnaps.models.Transform.objects.create(
            document_id=document,
            module='fake.module2',
            execution_priority=1)

        # Create Snapshot records.
        # Two existing snapshots for the single active job.
        docsnaps.models.Snapshot.objects.create(
            documents_languages_id=documents_languages,
            date=snapshot_datetime.date(),
            time=snapshot_datetime.time(),
            datetime=snapshot_datetime,
            text='Old snapshot. Slightly larger small document.')
        snapshot_datetime = snapshot_datetime + snapshot_timedelta
        docsnaps.models.Snapshot.objects.create(
            documents_languages_id=documents_languages,
            date=snapshot_datetime.date(),
            time=snapshot_datetime.time(),
            datetime=snapshot_datetime,
            text='Most recent snapshot. Really small document.')

    def test_database_error(self):
        """
        Test exception is properly bubbled when database error occurs.

        The error is re-raised as Django's CommandError.

        """
        mock_filter = mock.Mock(side_effect=django.db.Error)
        patch_target_obj = docsnaps.models.DocumentsLanguages.objects

        with mock.patch.object(patch_target_obj, 'filter', new=mock_filter):
            self.assertRaises(
                django.core.management.base.CommandError,
                self._command._get_active_jobs)

    def test_get_active_jobs_existent(self):
        """
        Test that correct result set was returned when there are active jobs.

        """
        active_jobs = self._command._get_active_jobs()

        self.assertEqual(len(active_jobs), 1)

    def test_get_active_jobs_nonexistent(self):
        """
        Test that empty result set was correctly returned when no active jobs.

        Django's TestCase wraps each test function in a transaction so
        database operations will not affect other test functios

        See:
            https://docs.djangoproject.com/en/dev/topics/testing/tools/#testcase

        """
        docsnaps.models.DocumentsLanguages.objects.all().update(
            is_enabled=False)
        active_jobs = self._command._get_active_jobs()

        self.assertEqual(len(active_jobs), 0)
