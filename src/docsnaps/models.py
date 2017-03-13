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
import django_forcedfields as forcedfields


class Company(models.Model):
    """
    A company or corporation.

    Although not necessary for snapshot job definitions, this extra model layer
    provides a logical way to organize snpashot jobs, especially for instances
    in which the resulting snapshot data is displayed in a UI.

    Unique natural key:

    Business or company names are registered by state in the U.S. Therefore, it
    is theoretically possible that two companies could have the same name. In
    addition, I am unfamiliar with global regulations, if any, so names may be
    duplicated within another country.

    Host names, however, must be unique within a TLD by technical necessity,
    although it is completely possible that a company may not have a web site.
    Another problem is that the same host name is used but the full URL is in a
    different format. For example, one host may use TLS while the other may not,
    even though both point to the same domain. I suspect this can be solved by
    field validators enforcing the omission of scheme and trailing slashes. If
    this field is used as any type of natural key in the future, it should be
    renamed to "url" or perhaps "hostname".

    Therefore, the Company name is the natural key. The cleanliness of the data
    (name duplication, spelling, etc.) will have to depend upon the user. We'l
    see how often names are duplicated.

    """

    company_id = models.AutoField(primary_key=True)
    name = models.CharField(
        blank=False, default=None, max_length=128, null=False, unique=True)
    website = models.URLField(
        blank=True, default=None, max_length=255, null=True)
    updated_timestamp = forcedfields.TimestampField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'company'


class Service(models.Model):
    """
    A service offered by a company.

    Natural key: a service in this app hinges upon some network resource. The
    Service, however, does not define the resource endpoint URI as that is
    described by the DocumentsLanguages model. Therefore, the website field is
    simply auxiliary metadata and the Service name combined with the Company is
    the natural key.

    """

    service_id = models.AutoField(primary_key=True)
    company_id = models.ForeignKey(
        Company, db_column='company_id', on_delete=models.PROTECT,
        verbose_name='company')
    name = models.CharField(
        blank=False, default=None, max_length=255, null=False)
    website = models.URLField(
        blank=True, default=None, max_length=255, null=True)
    updated_timestamp = forcedfields.TimestampField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'service'
        unique_together = ('company_id', 'name')


class Language(models.Model):
    """
    A language in which a document may be written.

    Natural key is the ISO code.

    May be redundant in light of Django's built-in support for language codes.
    However, it may be worth it to provide referential integrity in database.

    See:
        https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes

    """

    language_id = models.AutoField(primary_key=True)
    name = models.CharField(
        blank=False, default=None, max_length=255, null=False)
    code_iso_639_1 = forcedfields.FixedCharField(
        blank=False, default=None, max_length=2, null=False, unique=True,
        verbose_name='ISO 639-1 code')
    documents = models.ManyToManyField('Document', through='DocumentsLanguages')

    def __str__(self):
        return self.code_iso_639_1

    class Meta:
        db_table = 'language'


class Document(models.Model):
    """
    A document provided by a service.

    Natural key is the Service and the Document name.

    """

    document_id = models.AutoField(primary_key=True)
    service_id = models.ForeignKey(
        Service, db_column='service_id', on_delete=models.PROTECT,
        verbose_name='service')
    name = models.CharField(
        blank=False, default=None, max_length=255, null=False)
    updated_timestamp = forcedfields.TimestampField(auto_now=True)
    languages = models.ManyToManyField(Language, through='DocumentsLanguages')

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'document'
        unique_together = ('service_id', 'name')


class DocumentsLanguages(models.Model):
    """
    A many-to-many relationship between a document and a language.

    Represents a "document instance." This is the core of this app. The app
    will use this model to get a snapshot job's URI

    Experience has taught me the value of using a primary key on relationship
    records. In fact, look no further than the Snapshot model. Don't even bother
    asking me to remove the AutoField.

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
    url = models.URLField(
        blank=False, default=None, max_length=255, null=False)
    is_enabled = models.BooleanField(default=True)
    updated_timestamp = forcedfields.TimestampField(auto_now=True)

    class Meta:
        db_table = 'documents_languages'
        unique_together = ('document_id', 'language_id')
        verbose_name = 'document instance'


class Snapshot(models.Model):
    """
    A snapshot of a document in a given language.

    Date and time fields are separated for index and query optimization,
    datetime field used for ranges and range comparison.

    Note that there is no unique natural key, composite or otherwise. This
    leaves it completely to the users' discretion to decide snapshot intervals.

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
        unique_together = ['documents_languages_id', 'datetime']


class Transform(models.Model):
    """
    A transform class to which to pass a newly-fetched document snapshot.

    This table is designed to relate plugin modules and their supplied
    transforms to the documents they registered when installed.

    Natural key: the unique combination of document and module.
    There is currently no correct reason to double-register a module for the
    same snapshot job. When a plugin module's transform is passed data from a
    recent snapshot, it can internally differentiate between the document's
    language or other data. There is no reason to tie this relationship to the
    higher cardinality of DocumentsLanguages.

    The module field will contain absolute, fully-qualified module names that
    can be directly passed to importlib. Do not include the module's transform
    callable attribute in the name as that is part of the standardized interface
    and will be called automatically.

    Using a separate table rather than adding "module" to Documents
    allows for more flexible relationships, the addition of dependent fields,
    and for chained transform "pipelines" (see below).

    Execution priority exists so that multiple plugin modules can register to
    transform the same document. This forms a transform "pipeline" and allows
    altering transforms without having to edit third-party plugin module code.
    This field will largely be manually managed by the user. All records with
    identical priority returned by a given query will be sorted in arbitrary
    order to be determined by the DBMS.

    """

    transform_id = models.AutoField(primary_key=True)
    document_id = models.ForeignKey(
        Document, db_column='document_id',
        on_delete=models.PROTECT, verbose_name='document')
    module = models.CharField(
        blank=False, default=None, max_length=255, null=False)
    execution_priority = models.SmallIntegerField(default=0, null=False)

    class Meta:
        db_table = 'transform'
        unique_together = ('document_id', 'module')

