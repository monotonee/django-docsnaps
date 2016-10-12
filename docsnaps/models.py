"""
These models are designed to create migrations against its own database,
separate from Django's default database. Therefore, table names' redundant app
name prefixes are removed.

Table primary keys are more verbose than simply "id" as it makes foreign key
relations instantly tracable when looking at table schemas and makes writing raw
SQL more intuitive. Primary key fields and foreign key fields are named
identically.

Warning: foreign key constraints' ON DELETE actions are NOT defined in the raw
SQL and are therefore NOT present at the database level. Django "emulates" this
behavior. Default MariaDB and MySQL ON DELETE action is thankfully RESTRICT.

See:
    https://mariadb.com/kb/en/mariadb/foreign-keys/
    https://dev.mysql.com/doc/refman/5.7/en/create-table-foreign-keys.html#idm140349400499360

Note that I set NULL on all necessary fields, even Django's char fields. In a
database, a null value should represent the absence of information, not an
empty string. I greatly dislike Django's default behavior in this issue and I
refuse to compromise my schema for Django's opinionated idiosyncrasy. I will
find another solution to counter Django's use of empty strings.

See:
    https://docs.djangoproject.com/en/1.10/ref/models/fields/#null

According to PEP 8, this class name could contain capitalized "abbreviations"
(MariaDB instead of Mariadb) but MariaDB isn't an acronym such as HTTP and I
prefer to maintain the demarkation of words within the name. "MariaDB" could
potentially suggest that Maria and DB are separate parts.

See:
    https://www.python.org/dev/peps/pep-0008/#descriptive-naming-styles

"""

from django.db import models


class FixedCharField(models.CharField):
    """
    Stores Python strings in fixed-length "char" database fields.

    CharField's max_length kwarg is kept for simplicity. In this class, the
    value of max_length will be the length of the char field.

    This class is not currently designed for distribution and is an incomplete
    implementation of the solution.

    """

    def db_type(self, connection):
        if connection.settings_dict['ENGINE'] == 'django.db.backends.sqlite3':
            db_type = super().db_type(connection)
        else:
            db_type = 'char({!s})'.format(self.max_length)
        return db_type


class MariadbTimestampField(models.DateTimeField):
    """
    Stores Django model datetime objects into a MySQL/MariaDB TIMESTMAP column.

    This class is not currently designed for distribution and is an incomplete
    implementation of the solution.

    See:
        https://docs.djangoproject.com/en/dev/howto/custom-model-fields/

    """

    def db_type(self, connection):
        """
        The DateField/DateTimeField enforces mutual exclusivity between
        auto_now, auto_now_add, and default. Check is performed between call to
        db_type and the generation of actual SQL string. Therefore, these
        conflicting instance attributes cannot even be set internally here.

        As of MySQL 5.7 and MariaDB 10.1, TIMESTAMP fields are defaulted to
        auto-update with CURRENT_TIMESTAMP on creation and update of record.

        In MySQL/MariaDB, NULL, DEFAULT, and ON UPDATE are not mutually
        exclusive on a TIMESTAMP field.

        See:
            https://dev.mysql.com/doc/refman/5.7/en/timestamp-initialization.html
            https://mariadb.com/kb/en/mariadb/timestamp/

        In field deconstruction, Django's Field class uses the values from an
        instance's attributes rather than the passed **kwargs dict.

        See:
            https://github.com/django/django/blob/master/django/db/models/fields/__init__.py#L365

        """
        if connection.settings_dict['ENGINE'] == 'django.db.backends.mysql':
            type_spec = ['TIMESTAMP']
            ts_default_default = 'DEFAULT CURRENT_TIMESTAMP'
            ts_default_on_update = 'ON UPDATE CURRENT_TIMESTAMP'
            if self.auto_now:
                # CURRENT_TIMESTAMP on create and on update.
                # self.default = 'CURRENT_TIMESTAMP'
                type_spec.extend([ts_default_default, ts_default_on_update])
            elif self.auto_now_add:
                # CURRENT_TIMESTAMP on create only.
                # self.default = 'CURRENT_TIMESTAMP'
                type_spec.append(ts_default_default)
            elif self.has_default():
                # Set specified default on creation, no ON UPDATE action.
                type_spec.append('DEFAULT ' + str(self.default))
            elif not self.null:
                # Disable all default bahavior.
                self.default = 0
            db_type = ' '.join(type_spec)
        else:
            db_type = super().db_type(connection)

        return db_type


class Company(models.Model):
    """
    A company or corporation.

    """

    company_id = models.AutoField(primary_key=True)
    name = models.CharField(
        blank=False, default=None, max_length=128, null=False)
    website = models.URLField(
        blank=True, default=None, max_length=255, null=True)
    updated_timestamp = MariadbTimestampField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'company'


class Service(models.Model):
    """
    A service offered by a company.

    Address can be an IP address or an URL.

    """

    service_id = models.AutoField(primary_key=True)
    company_id = models.ForeignKey(
        Company, db_column='company_id', on_delete=models.PROTECT,
        verbose_name='company')
    name = models.CharField(
        blank=False, default=None, max_length=255, null=False)
    url = models.CharField(
        blank=False, default=None, max_length=255, null=False)
    updated_timestamp = MariadbTimestampField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'service'


class Language(models.Model):
    """
    A language in which a document may be written.

    May be redundant in light of Django's built-in support for language codes.
    However, it may be worth it to provide referential integrity in database.

    See:
        https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes

    """

    language_id = models.AutoField(primary_key=True)
    name = models.CharField(
        blank=False, default=None, max_length=255, null=False)
    code_iso_639_1 = FixedCharField(
        blank=False, default=None, max_length=2, null=False, unique=True,
        verbose_name='ISO 639-1 code')
    documents = models.ManyToManyField('Document', through='DocumentsLanguages')

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'language'


class Document(models.Model):
    """
    A document served by a service.

    """

    document_id = models.AutoField(primary_key=True)
    service_id = models.ForeignKey(
        Service, db_column='service_id', on_delete=models.PROTECT,
        verbose_name='service')
    name = models.CharField(
        blank=False, default=None, max_length=255, null=False)
    updated_timestamp = MariadbTimestampField(auto_now=True)
    languages = models.ManyToManyField(Language, through='DocumentsLanguages')

    class Meta:
        db_table = 'document'


class DocumentsLanguages(models.Model):
    """
    A many-to-many relationship between a document and a language.

    Experience has taught me the value of using a primary key on relationships.

    url_path is concatenated to the document's service address.
    is_enabled is a boolean value. When true, it indicates that the document, in
    the given language, is being polled with each poll cycle. This field is
    stored in the DB as a tinyint using eight bytes since MariaDB/MySQL stores
    bit fields in an integer type field (tinyint) anyway.

    """

    documents_languages_id = models.AutoField(primary_key=True)
    document_id = models.ForeignKey(
        Document, db_column='document_id', on_delete=models.PROTECT,
        verbose_name='document')
    language_id = models.ForeignKey(
        Language, db_column='language_id', on_delete=models.PROTECT,
        verbose_name='language')
    url = models.CharField(
        blank=False, default=None, max_length=255, null=False)
    is_enabled = models.BooleanField(default=False)
    updated_timestamp = MariadbTimestampField(auto_now=True)

    class Meta:
        db_table = 'documents_languages'
        unique_together = ('document_id', 'language_id')
        verbose_name = 'document instance'


class Snapshot(models.Model):
    """
    A snapshot of a document in a given language.

    Date and time fields are separated for index and query optimization,
    datetime field used for ranges and range comparison.

    """

    snapshot_id = models.AutoField(primary_key=True)
    documents_languages_id = models.ForeignKey(
        DocumentsLanguages, db_column='documents_languages_id',
        on_delete=models.PROTECT, verbose_name='document instance')
    date = models.DateField(null=False)
    time = models.TimeField(null=False)
    datetime = models.DateTimeField(db_index=True, null=False)
    text = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'snapshot'
        get_latest_by = 'datetime'
        index_together = ['date', 'time']


class Transform(models.Model):
    """
    A transform class to which to pass a newly-fetched doc snapshot.

    This table is designed to relate plugin modules and their supplied
    transforms to the documents they registered when installed.

    Using a separate table rather than adding "module" to DocumentsLanguages
    allows for more flexible relationships and for chained transforms.

    """

    transform_id = models.AutoField(primary_key=True)
    documents_languages_id = models.ForeignKey(
        DocumentsLanguages, db_column='documents_languages_id',
        on_delete=models.PROTECT, verbose_name='document instance')
    module = models.CharField(
        blank=False, default=None, max_length=255, null=False)
    execution_priority = models.SmallIntegerField(default=0, null=False)

    class Meta:
        db_table = 'transform'
        unique_together = ['documents_languages_id', 'module']

