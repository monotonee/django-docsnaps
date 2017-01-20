"""
Tests the selection of snapshot data from the database.

"""

import datetime
import io

from django.test import TestCase

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
        docsnaps.models.Snapshot.objects.create(
            documents_languages_id=documents_languages,
            date=snapshot_datetime.date().isoformat(),
            time=snapshot_datetime.time().isoformat(),
            datetime=snapshot_datetime.isoformat(),
            text='Slightly larger small document.')
        snapshot_datetime = snapshot_datetime + snapshot_timedelta
        docsnaps.models.Snapshot.objects.create(
            documents_languages_id=documents_languages,
            date=snapshot_datetime.date().isoformat(),
            time=snapshot_datetime.time().isoformat(),
            datetime=snapshot_datetime.isoformat(),
            text='Really small document')

    def test_get_latest_snapshots(self):
        """
        Test that the latest snapshot record was correctly selected.

        """
        #self._command._get_snapshots()
        raise NotImplementedError('Complete this test.')

    def test_execute_jobs_no_snapshots(self):
        """
        Test correct snapshot creation without any existing snapshots.

        """
        raise NotImplementedError('Complete this test.')


