"""
Tests the selection of job data from the database.

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


class TestExecuteJob(TestCase):

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

        # Create basic models.
        test_models = command_utils.flatten_model_graph(documents_languages)
        for model in reversed(list(test_models)):
            if isinstance(model, docsnaps.models.Document):
                document = model
            model.save()

        # Create Transform records.
        docsnaps.models.Transform.objects.create(
            document_id=document,
            module='fake.module1',
            execution_priority=0)
        docsnaps.models.Transform.objects.create(
            document_id=document,
            module='fake.module2',
            execution_priority=1)

        # Create Snapshot records.
        # Create old snapshot.
        docsnaps.models.Snapshot.objects.create(
            documents_languages_id=documents_languages,
            date=snapshot_datetime.date().isoformat(),
            time=snapshot_datetime.time().isoformat(),
            datetime=snapshot_datetime.isoformat(),
            text='Slightly larger small document.')
        # Create most recent snapshot.
        snapshot_datetime = snapshot_datetime + snapshot_timedelta
        docsnaps.models.Snapshot.objects.create(
            documents_languages_id=documents_languages,
            date=snapshot_datetime.date().isoformat(),
            time=snapshot_datetime.time().isoformat(),
            datetime=snapshot_datetime.isoformat(),
            text='Really small document')

    def test_execute_multiple_jobs(self):
        """
        Test correct snapshot creation under ideal conditions.

        """
        raise NotImplementedError('Complete this test.')

    def test_execute_single_job(self):
        """
        Test correct snapshot creation under ideal conditions.

        """
        #active_jobs = self._command._get_active_jobs()
        #loop = asyncio.get_event_loop()
        #loop.run_until_complete(self._command._execute_jobs(active_jobs))
        #loop.close()
        raise NotImplementedError('Complete this test.')

    def test_execute_single_job_no_snapshots(self):
        """
        Test correct snapshot creation without any existing snapshots.

        """
        raise NotImplementedError('Complete this test.')

    def test_job_exception(self):
        """
        Test behavior if a job completes with exception raised.

        Entire process should not be halted but failure should output to console
        and it should be logged.

        """
        pass
