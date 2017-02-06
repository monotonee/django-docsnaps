"""
Tests the selection of snapshot data from the database.

"""

import asyncio
import datetime
import io
import sys
import unittest.mock

from django.test import TestCase

# Preemptively replace settings module. Python will believe that the module has
# already been imported. The module's settings file imports the Django project
# settings module which, when running these tests outside of a Django project,
# obviously raises an exception. This must be done before the Command is
# imported.
sys.modules['docsnaps.settings'] = unittest.mock.NonCallableMock()

from .. import utils as test_utils
from docsnaps.management.commands._run import Command
import docsnaps.management.commands._utils as command_utils
import docsnaps.models


class TestGetSnapshots(TestCase):

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

    def test_get_latest_snapshot_single_job(self):
        """
        Test that the latest snapshot record was correctly selected.

        Two snapshots are defined in the test data but oly the latest for the
        active job should be returned.

        Calling close() on the event loop reference prevents other test cases
        from using the event loop.

        """
        loop = asyncio.get_event_loop()
        snapshots = loop.run_until_complete(self._command._get_snapshots())

        self.assertEqual(len(snapshots), 1)

    def test_get_latest_snapshot_multiple_jobs(self):
        """
        Test that latest snapshot record was correctly selected for each job.

        Only a single snapshot should be returned for each job, each of which
        should be the latest snapshot for the job.

        Calling close() on the event loop reference prevents other test cases
        from using the event loop.

        """
        # Create an additional active job.
        document_set = docsnaps.models.Document.objects.all()
        language_es = docsnaps.models.Language.objects.create(
            name='Spanish',
            code_iso_639_1='es')
        documents_languages = docsnaps.models.DocumentsLanguages.objects.create(
            document_id=document_set[0],
            language_id=language_es,
            url='help.test.tset/legal/termsofuse?locale=es',
            is_enabled=True)

        # Create two snapshots with sequential datetimes for new job.
        snapshot_timedelta = datetime.timedelta(days=2)
        snapshot_datetime = datetime.datetime.today() - snapshot_timedelta
        docsnaps.models.Snapshot.objects.create(
            documents_languages_id=documents_languages,
            date=snapshot_datetime.date(),
            time=snapshot_datetime.time(),
            datetime=snapshot_datetime,
            text='Old snapshot. Slightly larger small document 2.')
        snapshot_datetime = snapshot_datetime + snapshot_timedelta
        docsnaps.models.Snapshot.objects.create(
            documents_languages_id=documents_languages,
            date=snapshot_datetime.date(),
            time=snapshot_datetime.time(),
            datetime=snapshot_datetime,
            text='Most recent snapshot. Really small document 2.')

        loop = asyncio.get_event_loop()
        snapshots = loop.run_until_complete(self._command._get_snapshots())

        self.assertEqual(len(snapshots), 2)

    def test_execute_jobs_no_snapshots(self):
        """
        Test correct snapshot query without any existing snapshots.

        """
        docsnaps.models.Snapshot.objects.all().delete()

        loop = asyncio.get_event_loop()
        snapshots = loop.run_until_complete(self._command._get_snapshots())

        self.assertEqual(len(snapshots), 0)


