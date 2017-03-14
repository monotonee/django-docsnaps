"""
These models are designed to create migrations against its own database,
separate from Django's default database. Therefore, table names' redundant app
name prefixes are removed.

Table primary keys are more verbose than simply "id" as it makes foreign key
relations instantly tracable when looking at table schemas and makes writing raw
SQL more intuitive. In addition, primary key fields and foreign key fields are
named identically.

Warning: foreign key constraints' ON DELETE actions are NOT defined in the raw
SQL and are therefore NOT present at the database level. Django "emulates" this
behavior. Default MariaDB and MySQL ON DELETE action is thankfully RESTRICT.

See:
    https://mariadb.com/kb/en/mariadb/foreign-keys/
    https://dev.mysql.com/doc/refman/en/create-table-foreign-keys.html#idm140349400499360

Note that I set NULL on all necessary fields, even Django's char fields. In a
database, a null value should represent the absence of information, not an
empty string. I greatly dislike Django's default behavior in this issue and I
refuse to compromise my schema for Django's opinionated idiosyncrasy. I will
find another solution to counter Django's use of empty strings.

See:
    https://docs.djangoproject.com/en/dev/ref/models/fields/#null

"""

import django.db.models
import django_forcedfields as forcedfields


class Document(django.db.models.Model):
    """
    A document that will be monitored for changes.

    The natural key is the module and the document name. This does allow for
    possible document duplication but it is primarily the user's
    responsibility to check when installing new snapshot jobs via plugin modules
    or even manually through direct record insertion.

    """

    document_id = django.db.models.AutoField(primary_key=True)
    module = django.db.models.CharField(
        blank=False,
        default=None,
        max_length=255,
        null=False,
        help_text=(
            'The name of the module from which this record was installed.'))
    name = django.db.models.CharField(
        blank=False,
        default=None,
        max_length=255,
        null=False,
        help_text='The name of the document.')
    updated_timestamp = forcedfields.TimestampField(auto_now=True)
    languages = django.db.models.ManyToManyField(
        'Language', through='DocumentsLanguages')

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'document'
        unique_together = ('module', 'name')


class Language(django.db.models.Model):
    """
    A language in which a document may be written.

    Natural key is the ISO code.

    May be redundant in light of Django's built-in support for language codes.
    However, it may be worth it to provide referential integrity in database.

    See:
        https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes

    """

    language_id = django.db.models.AutoField(primary_key=True)
    name = django.db.models.CharField(
        blank=False,
        default=None,
        max_length=255,
        null=False)
    code_iso_639_1 = forcedfields.FixedCharField(
        blank=False,
        default=None,
        max_length=2,
        null=False,
        unique=True,
        verbose_name='ISO 639-1 code')
    documents = django.db.models.ManyToManyField(
        Document, through='DocumentsLanguages')

    def __str__(self):
        return self.code_iso_639_1

    class Meta:
        db_table = 'language'


class DocumentsLanguages(django.db.models.Model):
    """
    A many-to-many relationship between a document and a language.

    Represents a "document instance." This is the core of this app. The app
    will use this model to get a snapshot job's URI

    Experience has taught me the value of using an auto-generated primary key on
    records that describe a relationship. In fact, look no further than the
    Snapshot model for an illustration of the PK utility. Don't even bother
    asking me to remove the AutoField.

    is_enabled is a boolean value. When true, it indicates that the document, in
    the given language, is being polled with each job execution. This field is
    stored in the DB as a tinyint using eight bytes since MariaDB/MySQL stores
    bit fields in an integer type field (tinyint) anyway.

    """

    documents_languages_id = django.db.models.AutoField(primary_key=True)
    document_id = django.db.models.ForeignKey(
        Document,
        db_column='document_id',
        on_delete=django.db.models.PROTECT,
        verbose_name='document')
    language_id = django.db.models.ForeignKey(
        Language,
        db_column='language_id',
        on_delete=django.db.models.PROTECT,
        verbose_name='language')
    url = django.db.models.URLField(
        blank=False, default=None, max_length=255, null=False)
    is_enabled = django.db.models.BooleanField(default=True)
    updated_timestamp = forcedfields.TimestampField(auto_now=True)

    class Meta:
        db_table = 'documents_languages'
        unique_together = ('document_id', 'language_id')
        verbose_name = 'document instance'


class Snapshot(django.db.models.Model):
    """
    A snapshot of a document in a given language.

    Discrete date and time fields are separated for index and query optimization
    and a datetime field is used for ranges and range comparison.

    """

    snapshot_id = django.db.models.AutoField(primary_key=True)
    documents_languages_id = django.db.models.ForeignKey(
        DocumentsLanguages,
        db_column='documents_languages_id',
        on_delete=django.db.models.PROTECT,
        verbose_name='document instance')
    date = django.db.models.DateField(null=False)
    time = django.db.models.TimeField(null=False)
    datetime = django.db.models.DateTimeField(db_index=True, null=False)
    text = django.db.models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'snapshot'
        get_latest_by = 'datetime'
        index_together = ['date', 'time']
        unique_together = ['documents_languages_id', 'datetime']


# class Transform(models.Model):
    # """
    # A transform class to which to pass a newly-fetched document snapshot.

    # This table is designed to relate plugin modules and their supplied
    # transforms to the documents they registered when installed.

    # Natural key: the unique combination of document and module.
    # There is currently no correct reason to double-register a module for the
    # same snapshot job. When a plugin module's transform is passed data from a
    # recent snapshot, it can internally differentiate between the document's
    # language or other data. There is no reason to tie this relationship to the
    # higher cardinality of DocumentsLanguages.

    # The module field will contain absolute, fully-qualified module names that
    # can be directly passed to importlib. Do not include the module's transform
    # callable attribute in the name as that is part of the standardized interface
    # and will be called automatically.

    # Using a separate table rather than adding "module" to Documents
    # allows for more flexible relationships, the addition of dependent fields,
    # and for chained transform "pipelines" (see below).

    # Execution priority exists so that multiple plugin modules can register to
    # transform the same document. This forms a transform "pipeline" and allows
    # altering transforms without having to edit third-party plugin module code.
    # This field will largely be manually managed by the user. All records with
    # identical priority returned by a given query will be sorted in arbitrary
    # order to be determined by the DBMS.

    # """

    # transform_id = models.AutoField(primary_key=True)
    # document_id = models.ForeignKey(
        # Document, db_column='document_id',
        # on_delete=models.PROTECT, verbose_name='document')
    # module = models.CharField(
        # blank=False, default=None, max_length=255, null=False)
    # execution_priority = models.SmallIntegerField(default=0, null=False)

    # class Meta:
        # db_table = 'transform'
        # unique_together = ('document_id', 'module')

