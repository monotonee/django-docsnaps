"""
A Django admin command that will run all enabled snapshot jobs.

Note that exceptions are caught in each private method instead of using a single
try-except block in the handle() method. This is done to allow more specificity
of exception classes in the except clause. Due to the wide array of operations
occurring under the handle() method, the set of possible exception classes
becomes too large and increases the risk of catching an exception that should
be allowed to bubble.

TODO: Consider adding a CLI argument to run one or more specific jobs.
TODO: Create CLI status indicators for each async task. Will require multi-line
    terminal space allocation and tracking of task-to-line association since
    async execution will scramble output order.
TODO: Remove database exception handling? handlers don't do anything but throw
    a CommandError. DB exceptions should have same effect if left to bubble.

"""

import asyncio
import importlib

import aiohttp
import django.conf
import django.core.management.base
import django.db

import django_docsnaps.models
import django_docsnaps.management.commands._utils as command_utils
import django_docsnaps.settings


class Command(django.core.management.base.BaseCommand):

    help = 'Executes active jobs and saves snapshots of changed documents.'

    def _get_active_jobs(self):
        """
        Query the database for active snapshot jobs.

        Each DocumentsLanguages record corresponds to a snpashot "job." Each job
        may have zero or more Snapshot records which are queried and returned
        in a separate method.

        Returns:
            iterable: When not empty, elements are DocumentsLanguages model
            instances.

        Raises:
            django.core.management.base.CommandError: If exception is raised by
                underlying database library.

        See:
            https://docs.djangoproject.com/en/dev/topics/db/sql/#adding-annotations

        """
        self.stdout.write('Querying enabled snapshot jobs: ', ending='')

        try:
            docsnaps_set = django_docsnaps.models.DocumentsLanguages.objects\
                .filter(is_enabled=True)
        except django.db.Error as exception:
            command_utils.raise_command_error(
                self.stdout,
                'A database error occurred: ' + str(exception))

        self.stdout.write(self.style.SUCCESS('success'))
        return docsnaps_set

    async def _get_latest_snapshots(self):
        """
        Get the latest document snapshot for each active job.

        This was defined in its own method for a number of reasons.

        As the docsnaps system runs and accumulates potentially hundreds or even
        thousands of document snapshots, it becomes unfeasable and detrimental
        to attempt to load all snapshot records. Therefore, some method must be
        found to limit the results to the latest snapshot. In-memory sorting is
        not ideal inside a web application. The database layer is the
        appropriate and most efficient place to perform sorting and limiting but
        a more complex query is required.

        I use a self-join to find the latest Snapshot record for each
        DocumentsLanguages record. I am tired of fighting with the ORM for
        everything but the most basic queries. I am therefore using a raw SQL
        string.

        Note the added "raw" field in the SELECT query. Attempting to get the
        documents_languages_id from the Snapshot field causes the ORM to issue
        a separate query for each documents_languages_id since the field is a
        DocumentsLanguages instance. By using the ORM's annotation feature with
        raw(), I can get the simple integer documents_languages_id without
        loading an entire DocumentsLanguages instance data from the database.

        Returns:
            dict: A dictionary of the latest Snapshot text for each
            Documentslanguages record, keyed by the snapshot's
            documents_languages_id.

        """
        snapshot_sql = '''
            SELECT
                {Snapshot}.snapshot_id
                ,{Snapshot}.documents_languages_id
                ,{Snapshot}.date
                ,{Snapshot}.time
                ,{Snapshot}.datetime
                ,{Snapshot}.text
                ,{Snapshot}.documents_languages_id AS raw_documents_languages_id
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
        dl_db_table = django_docsnaps.models.DocumentsLanguages._meta.db_table
        s_db_table = django_docsnaps.models.Snapshot._meta.db_table
        snapshot_sql = snapshot_sql.format(
            DocumentsLanguages=dl_db_table,
            Snapshot=s_db_table)

        try:
            snapshot_set = django_docsnaps.models.Snapshot.objects.raw(
                snapshot_sql)
        except django.db.Error as exception:
            command_utils.raise_command_error(
                self.stdout,
                'A database error occurred: ' + str(exception))

        snapshot_dict = {
            snapshot.raw_documents_languages_id: snapshot \
            for snapshot in snapshot_set}

        return snapshot_dict

    async def _execute_single_job(self, job, client_session, snapshot=None):
        """
        Execute a single snapshot job.

        Args:
            job (django_docsnaps.models.DocumentsLanguages): A
                DocumentsLanguages model instance. This model class represents
                a snapshot job on which is_enabled=True.
            client_session: An HTTP request session. In aiohttp, for
                example, this is a ClientSession object, an abstraction of a
                connection pool.
            snapshot (django_docsnaps.models.Snapshot): The latest
                Snapshot record created by the job. When None, no Snapshot
                record yet exists.

        """
        doc_text = await self._request_document(client_session, job.url)
        job_module = self._import_job_module(job)
        transformed_doc_text, doc_is_changed = job_module.transform(doc_text)
        if doc_is_changed:
            await self._save_new_snapshot(job, transformed_doc_text)
        else:
            # Do something here. Status message.
            pass

    async def _execute_enabled_jobs(self, active_jobs, loop=None):
        """
        Execute each job in the passed iterable of snapshot jobs.

        This method manages the creation of coroutines, task objects, task
        scheduling, and the creation of the aiohttp session.

        Defined in own function to reduce nested block levels in the handle()
        method. In addition, I find it more semantic to separate domain logic
        from generic argparse interface methods such as handle().

        Defined as a coroutine to shut aiohttp up. aiohttp apparently issues
        warnings directly to stdout when one tries to use a ClientSession
        while loop is not running. I have yet to find documentation on the
        technical reasons for this requirement.

        Args:
            active_jobs (iterable): An iterable of DocumentsLanguages model
                instances representing records in which is_enabled is True.

        """
        if not loop:
            loop = asyncio.get_event_loop()

        snapshots = await self._get_latest_snapshots()

        with aiohttp.ClientSession(loop=loop) as client_session:
            tasks = []
            for job in active_jobs:
                snapshot = snapshots.get(job.documents_languages_id, None)
                task = loop.create_task(
                    self._execute_single_job(
                        job, client_session, snapshot=snapshot))
                tasks.append(task)

            done, pending = await asyncio.wait(tasks)

    def _import_job_module(self, job):
        """
        Attempt to import the job's module.

        Each job (DocumentsLanguages model instance) is associated with a Python
        module. This module is responsible for, at the very least, deciding if
        a new document snapshot needs to be saved and if any transformations to
        the document text need to be applied.

        Args:
            job (django_docsnaps.models.DocumentsLanguages): A
                DocumentsLanguages model instance. This model class represents
                a snapshot job on which is_enabled=True.

        Returns:
            module: The Python module object returned by importlib.

        Raises:
            django.core.management.base.CommandError: If module cannot be
                imported.

        """
        try:
            module = importlib.import_module(job.document_id.module)
        except ImportError as exception:
            exception_message = (
                'The module "{!s}" for snapshot job "{!s}" could not be '
                'imported.')
            exception_message = exception_message.format(
                job.document_id.module,
                job.document_id.name)
            command_utils.raise_command_error(self.stdout, exception_message)

        return module

    async def _request_document(self, client_session, url):
        """
        Request the document from the remote source.

        May need more robust response handling than raise_for_status().
        Note that aiohttp's ClientSession will follow redirects by default.

        Possible errors:
            aiohttp.errors.ClientError
                Client connection errors.
            aiohttp.errors.HttpProcessingError
                From response.raise_for_status().
            aiohttp.errors.ClientTimeoutError
                ClientTimeoutError inherits from both ClientError (ancestor to
                parent ClientConnectionError) and asyncio.TimeoutError.
                aiohttp.errors.TimeoutError is a passthrough of
                asyncio.TimeoutError.

        See:
            https://github.com/aio-libs/aiohttp/blob/1.3/aiohttp/errors.py
            https://github.com/aio-libs/aiohttp/blob/1.3/aiohttp/client_reqrep.py
            https://aiohttp.readthedocs.io/en/stable/client_reference.html#aiohttp.ClientResponse.raise_for_status

        Args:
            client_session: An HTTP request session. In aiohttp, for
                example, this is a ClientSession object, an abstraction of a
                connection pool.
            url (string): The URL to which a GET request will be issued.

        Returns:
            string: A string of the fetched document.

        Raises:
            django.core.management.base.CommandError: If any HTTP request
                exceptions are raised by underlying HTTP library.

        """
        timeout = django_docsnaps.settings.DJANGO_DOCSNAPS_REQUEST_TIMEOUT
        response_text = None
        try:
            async with client_session.get(url, timeout=timeout) as response:
                response.raise_for_status()
                response_text = await response.text()
        except (
            asyncio.errors.ClientError,
            aiohttp.errors.HttpProcessingError) as exception:
            exception_message = (
                'The request for the document at URL "{!s}" failed with the '
                'following exception: ')
            exception_message.format(url)
            comamnd_utils.raise_commend_error(
                self.stdout,
                exception_message + str(exception))

        return response_text

    async def _save_new_snapshot(self, job, snapshot_text):
        """
        Save a new document snapshot in the database for the passed job.

        Args:
            job (django_docsnaps.models.DocumentsLanguages): A
                DocumentsLanguages model instance. This model class represents
                a snapshot job on which is_enabled=True.
            snapshot_text (string): The text of the new document snapshot.

        Returns:
            django_docsnaps.models.Snapshot: The new Snapshot model instance
                after save() has been called.

        Raises:
            Raises:
            django.core.management.base.CommandError: If exception is raised by
                underlying database library.

        """
        new_snapshot = django_docsnaps.models.Snapshot(
            documents_languages_id=job,
            text=snapshot_text)
        new_snapshot.save()

        return new_snapshot

    def add_arguments(self, parser):
        """
        Add arguments to the argparse parser object.

        Currently no need for arguments.

        Add a dry-run flag?

        """
        pass

    def handle(self, *args, **options):
        enabled_jobs = self._get_active_jobs()
        if enabled_jobs:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(
                self._execute_enabled_jobs(enabled_jobs, loop=loop))
            loop.close()
            run_status = self.style.SUCCESS(
                'Active jobs completed successfully.')
        else:
            run_status = self.style.WARNING('No active jobs found.')

        self.stdout.write('Job execution complete: ' + run_status)
