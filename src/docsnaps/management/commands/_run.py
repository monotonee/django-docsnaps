"""
A Django admin command that will run all enabled snapshot jobs.

TODO: Consider adding a CLI argument to run one or more specific jobs.
TODO: Create CLI status indicators for each async task. Will require multi-line
    terminal space allocation and tracking of task-to-line association since
    async execution will scramble output order.
TODO: Remove database exception handling? handlers don't do anything but throw
    a CommandError. DB exceptions should have same effect if left to bubble.

"""

import asyncio
#from importlib import import_module

import aiohttp
from django.core.management.base import BaseCommand, CommandError
import django.db
from django.db.models import prefetch_related_objects

import docsnaps.models
import docsnaps.management.commands._utils as command_utils
import docsnaps.settings


class Command(BaseCommand):

    help = 'Executes active snapshot jobs and saves snapshots of changed docs.'

    def _get_active_jobs(self):
        """
        Query the database for active snapshot jobs.

        Each DocumentsLanguages record corresponds to a snpashot "job." Each job
        may have zero or more Snapshot records which are queried and returned
        in a separate method.

        Returns:
            An iterable. When not empty, elements are DocumentsLanguages model
            instances.

        See:
            https://docs.djangoproject.com/en/dev/topics/db/sql/#adding-annotations

        """
        self.stdout.write('Loading enabled snapshot jobs: ', ending='')

        command_error_message = None
        try:
            docsnaps_set = docsnaps.models.DocumentsLanguages.objects.filter(
                is_enabled=True)
        except django.db.Error as exception:
            command_error_message = (
                'A database error occurred: ' + str(exception))

        if command_error_message:
            command_utils.raise_command_error(
                self.stdout,
                command_error_message)

        self.stdout.write(self.style.SUCCESS('success'))
        return docsnaps_set

    async def _execute_jobs(self, active_jobs):
        """
        Execute each job in the passed iterable of snapshot jobs.

        Defined in own function to reduce nested block levels in the handle()
        method. This method handles the creation of event loop, coroutine
        creation and scheduling, and the aiohttp session creation.

        Defined as a coroutine to shut aiohttp up. aiohttp apparently issues
        warnings directly to stdout when one tries to use a ClientSession
        while loop is not running. I have yet to find documentation on the
        technical reasons for this requirement.

        Args:
            active_jobs (iterable): An iterable of DocumentsLanguages model
                instances representing records in which is_enabled is True.

        """
        snapshots = await self._get_snapshots()

        loop = asyncio.get_event_loop()
        with aiohttp.ClientSession() as client_session:
            tasks = []
            for job in active_jobs:
                snapshot = snapshots.get(job.documents_languages_id, None)
                task = loop.create_task(
                    self._execute_job(job, client_session, snapshot))
                tasks.append(task)

            done, pending = await asyncio.wait(tasks)

    async def _execute_job(self, job, client_session, snapshot_text=None):
        """
        Execute a single snapshot job.

        Args:
            job (DocumentsLanguages): A DocumentsLanguages model instance.
            snapshot_text (string): The text of the job's most recent snapshot.
            client_session: An HTTP request session. In aiohttp, for
                example, this is a ClientSession object, an abstraction of a
                connection pool.

        """
        new_snapshot = await self._request_document(client_session, job.url)
        self.stdout.write('Pre-sleep')
        await asyncio.sleep(1)
        self.stdout.write('Post-sleep')
        raise Exception('test')

    async def _request_document(self, client_session, url):
        """
        Request the document from the remote source.

        May need more robust response handling than raise_for_status().

        Args:
            client_session: An HTTP request session. In aiohttp, for
                example, this is a ClientSession object, an abstraction of a
                connection pool.
            url (string): The URL to which a GET request will be issued.

        Returns:
            string: A string of the fetched document.

        """
        response = await client_session.get(
            url,
            timeout=docsnaps.settings.DOCSNAPS_REQUEST_TIMEOUT)
        response.raise_for_status()
        response_text = await response.text()
        response.close()

        return response_text

    async def _get_snapshots(self):
        """
        Get the latest document snapshot for each active job.

        This was defined in its own method for a number of reasons.

        As the docsnaps system runs and accumulates potentially hundreds or even
        thousands of document snapshots, it becomes unfeasable and detrimental
        to attempt to load all snapshot records. Therefore, some method must be
        found to limit the results to the latest snapshot. In-memory sorting is
        impractical with high cardinality. The database layer is the appropriate
        place to perform sorting and limiting but a more complex query is
        required.

        I use a self-join to find the latest Snapshot record for each
        DocumentsLanguages record. I am tired of fighting with the ORM for
        everything but the most basic queries. I am therefore using a raw SQL
        string.

        I refuse to use manager.raw() as select_related() is not supported and
        the Snapshot models will issue a separate query for EVERY
        DocumentsLanguages PK access.

        The only other alternative is to use QuerySet.iterator() to look for and
        save the latest Snapshot for each DocumentsLanguages record. However,
        this still requires iterating over EVERY active snapshot record. ORM
        layers are such double-edged swords and are meant for nothing more
        complex than simple web sites.

        Returns:
            dict: A dictionary of the latest Snapshot text for each
            Documentslanguages record, keyed by the snapshot's
            documents_languages_id.

        """
        snapshot_sql = '''
            SELECT
                {Snapshot}.snapshot_id
                ,{Snapshot}.documents_languages_id
                ,{Snapshot}.text
            FROM
                {Snapshot}
                LEFT JOIN {Snapshot} as snapshot_2
                    ON snapshot_2.documents_languages_id = {Snapshot}.documents_languages_id
                    AND snapshot_2.datetime > {Snapshot}.datetime
                INNER JOIN {DocumentsLanguages}
                    ON {DocumentsLanguages}.documents_languages_id = {Snapshot}.documents_languages_id
                    AND {DocumentsLanguages}.is_enabled IS TRUE
            WHERE
                snapshot_2.snapshot_id IS NULL'''
        snapshot_sql = snapshot_sql.format(
            DocumentsLanguages=docsnaps.models.DocumentsLanguages._meta.db_table,
            Snapshot=docsnaps.models.Snapshot._meta.db_table)

        command_error_message = None
        try:
            with django.db.connection.cursor() as cursor:
                cursor.execute(snapshot_sql)
                result_set = cursor.fetchall()
        except django.db.Error as exception:
            command_error_message = (
                'A database error occurred: ' + str(exception))

        if command_error_message:
            command_utils.raise_command_error(
                self.stdout,
                command_error_message)

        snapshot_dict = {snapshot[1]: snapshot[2] for snapshot in result_set}
        return snapshot_dict

    def add_arguments(self, parser):
        """
        Add arguments to the argparse parser object.

        Currently no need for arguments.

        Add a dry-run flag?

        """
        pass

    def handle(self, *args, **options):
        active_jobs = self._get_active_jobs()
        if (active_jobs):
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self._execute_jobs(active_jobs))
            loop.close()
