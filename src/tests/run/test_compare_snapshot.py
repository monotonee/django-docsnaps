"""
Tests the comparison of a new snapshot to the most recent existing snapshot.

This operation is executed after fetching a new document snapshot from a remote
source.

"""

import asyncio
import datetime
import io

from django.test import TestCase

from .. import utils as test_utils
from docsnaps.management.commands._run import Command
import docsnaps.management.commands._utils as command_utils
import docsnaps.models


class TestCompareSnapshot(TestCase):

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

    def test_multiple_transforms_available(self):
        """
        Test importing module and applying transforms in order successfully.

        Transform must be applied before comparing new and existing document
        snapshots. Multiple transforms may be registered for a single document
        snapshot job, ordered by a "priority" ordinal. Ensure that all
        transforms are executed and executed in the correct order.

        """
        raise NotImplementedError('Complete this test.')

    def test_no_existing_snapshot(self):
        """
        Test comparison when no existing snapshot exists.

        This condition occurs when running a snapshot job for the first time.

        """
        raise NotImplementedError('Complete this test.')

    def test_snapshot_changed(self):
        """
        Test new document snapshot different than existing, most recent one.

        """
        raise NotImplementedError('Complete this test.')

    def test_snapshot_unchanged(self):
        """
        Test new document snapshot unchanged from existing, most recent one.

        """
        raise NotImplementedError('Complete this test.')

    def test_transform_available(self):
        """
        Test importing module and applying transform successfully.

        Transform must be applied before comparing new and existing document
        snapshots.

        """
        raise NotImplementedError('Complete this test.')

    def test_transform_module_load_failure(self):
        """
        Test failure to import module that contains the transform.

        """
        raise NotImplementedError('Complete this test.')

    def test_transform_unavailable(self):
        """
        Test importing module when no transform available.

        In this case, raw document snapshot will be compared.

        """
        raise NotImplementedError('Complete this test.')
