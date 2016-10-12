"""
A Django admin command that will run all enabled snapshot jobs.

"""

from django.core.management.base import BaseCommand, CommandError
from django.db.models import prefetch_related_objects
from importlib import import_module

import requests

from ...models import DocumentsLanguages


HELP = 'Executes active snapshot jobs and saves snapshots of changed docs.'

def _compare_snapshot(instance, text):
    """
    Determine if new text has changed since last snapshot.

    Args:
        instance (models.DocumentsLanguages): Model of a doc instance.
            Necessary to fetch most reent snapshot of doc instance.
        text (string): The text of the document after transformation.

    Returns:
        Boolean True if changed, False, otherwise.

    """
    pass


def _save_document(instance, text):
    """
    Save the document text to the database.

    Writes status details to self.stdout.

    Args:
        instance (models.DocumentsLanguages): Model of a doc instance.
        text (string): The raw text of the document as received from the
            source.

    """
    pass

def _transform_document(instance, text):
    """
    Check for transformers for document and apply them if available.

    Writes status details to self.stdout.

    Args:
        instance (models.DocumentsLanguages): Model of a doc instance.
            Necessary to determine name of transformer class.
        text (string): The raw text of the document as received from the
            source.

    Returns:
        Text of document after transformations have been applied, if any
            were available.

    """
    return_text = text

    self.stdout.write('  ' + 'Searching for transformation: ', ending='')
    module_name = instance.service_name.lower().replace(' ', '_')
    root_pkg = __name__.split('.')[0]
    transformers_pkg = '.'.join([root_pkg, 'transformers'])

    try:
        module = import_module('.'.join([transformers_pkg, module_name]))
    except ImportError:
        pass
    else:
        # If language-specific transformer available, give it priority.
        doc_name = instance.document_id.name.title().replace(' ', '')
        lang_code = instance.language_id.code_iso_639_1.title()
        transformer = None
        if hasattr(module, doc_name + lang_code):
            transformer_class = getattr(module, doc_name + lang_code)
            transformer = transformer_class()
        elif hasattr(module, doc_name):
            transformer_class = getattr(module, doc_name)
            transformer = transformer_class()

        if transformer:
            self.stdout.write(self.style.SUCCESS('found'))
            self.stdout.write('  ' + 'Applying transformation: ', ending='')
            return_text = transformer.transform(text)
            self.stdout.write(self.style.SUCCESS('done'))
        else:
            self.stdout.write(self.style.warning('not found'))

    return return_text

def handle(*args, **options):
    """
    Checks the content of each document and saves those that have changed.

    I'm tired of fighting with the ORM for everything but the most basic
    queries. Despite the use of prefetch_related, Django will still issue a
    separate SQL query for most methods that operate upon the set, defeating
    the purpose of prefetching in this context. This essentialy limits me to
    using .all() and performing sorts, slicing, and filters manually in
    Python. This is not future-proof (large data sets) and it violates
    logical duties of the code/database separation. Raw SQL is therefore
    used.

    Attempting to use django.db.models.prefetch_related_objects() results
    in a separate query for each related object, which again defeats my
    reasonable goal of minimizing database hits.

    See:
        https://docs.djangoproject.com/en/dev/topics/db/sql/#adding-annotations
        https://docs.djangoproject.com/en/dev/ref/models/querysets/#prefetch-related
        https://docs.djangoproject.com/en/1.10/ref/models/querysets/#prefetch-related-objects

    """
    # Note that newlines and spaces are preserved in this string. Machines
    # don't care and code as read more than it is written.
    raw_sql = '''
        SELECT
            documents_languages.*,
            service.name as service_name,
            document.name AS document_name,
            language.name AS language_name,
            language.code_iso_639_1 AS language_code_iso_639_1,
            snapshot.text AS latest_snapshot_text
        FROM
            documents_languages
            INNER JOIN document
                ON document.document_id = documents_languages.document_id
            INNER JOIN language
                ON language.language_id = documents_languages.language_id
            INNER JOIN service
                ON service.service_id = document.service_id
            LEFT JOIN snapshot
                ON snapshot.documents_languages_id = documents_languages.documents_languages_id
            LEFT JOIN snapshot AS snapshot2
                ON snapshot2.documents_languages_id = documents_languages.documents_languages_id
                AND snapshot2.datetime > snapshot.datetime
        WHERE
            documents_languages.is_enabled IS TRUE
            AND snapshot2.snapshot_id IS NULL'''
    doc_instances = DocumentsLanguages.objects.raw(raw_sql)

    for instance in doc_instances:
        self.stdout.write(self.style.MIGRATE_HEADING(' '.join([
            instance.service_name,
            instance.document_name,
            'in',
            instance.language_name])))

        self.stdout.write('  Requesting document: ', ending='')
        try:
            response = requests.get('https://' + instance.url)
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            self.stdout.write(self.style.ERROR(response.status_code))
        except requests.exceptions.RequestException as exception:
            self.stdout.write(self.style.ERROR(type(exception).__name__))
        else:
            self.stdout.write(self.style.SUCCESS(response.status_code))
            text = self._transform_document(instance, response.text)
