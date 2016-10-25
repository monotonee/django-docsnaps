# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2016-10-25 20:23
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import docsnaps.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Company',
            fields=[
                ('company_id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(default=None, max_length=128, unique=True)),
                ('website', models.URLField(blank=True, default=None, max_length=255, null=True)),
                ('updated_timestamp', docsnaps.models.MariadbTimestampField(auto_now=True)),
            ],
            options={
                'db_table': 'company',
            },
        ),
        migrations.CreateModel(
            name='Document',
            fields=[
                ('document_id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(default=None, max_length=255)),
                ('updated_timestamp', docsnaps.models.MariadbTimestampField(auto_now=True)),
            ],
            options={
                'db_table': 'document',
            },
        ),
        migrations.CreateModel(
            name='DocumentsLanguages',
            fields=[
                ('documents_languages_id', models.AutoField(primary_key=True, serialize=False)),
                ('url', models.URLField(default=None, max_length=255)),
                ('is_enabled', models.BooleanField(default=False)),
                ('updated_timestamp', docsnaps.models.MariadbTimestampField(auto_now=True)),
                ('document_id', models.ForeignKey(db_column='document_id', on_delete=django.db.models.deletion.PROTECT, to='docsnaps.Document', verbose_name='document')),
            ],
            options={
                'verbose_name': 'document instance',
                'db_table': 'documents_languages',
            },
        ),
        migrations.CreateModel(
            name='Language',
            fields=[
                ('language_id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(default=None, max_length=255)),
                ('code_iso_639_1', docsnaps.models.FixedCharField(default=None, max_length=2, unique=True, verbose_name='ISO 639-1 code')),
                ('documents', models.ManyToManyField(through='docsnaps.DocumentsLanguages', to='docsnaps.Document')),
            ],
            options={
                'db_table': 'language',
            },
        ),
        migrations.CreateModel(
            name='Service',
            fields=[
                ('service_id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(default=None, max_length=255)),
                ('website', models.URLField(blank=True, default=None, max_length=255, null=True)),
                ('updated_timestamp', docsnaps.models.MariadbTimestampField(auto_now=True)),
                ('company_id', models.ForeignKey(db_column='company_id', on_delete=django.db.models.deletion.PROTECT, to='docsnaps.Company', verbose_name='company')),
            ],
            options={
                'db_table': 'service',
            },
        ),
        migrations.CreateModel(
            name='Snapshot',
            fields=[
                ('snapshot_id', models.AutoField(primary_key=True, serialize=False)),
                ('date', models.DateField()),
                ('time', models.TimeField()),
                ('datetime', models.DateTimeField(db_index=True)),
                ('text', models.TextField(blank=True, null=True)),
                ('documents_languages_id', models.ForeignKey(db_column='documents_languages_id', on_delete=django.db.models.deletion.PROTECT, to='docsnaps.DocumentsLanguages', verbose_name='document instance')),
            ],
            options={
                'get_latest_by': 'datetime',
                'db_table': 'snapshot',
            },
        ),
        migrations.CreateModel(
            name='Transform',
            fields=[
                ('transform_id', models.AutoField(primary_key=True, serialize=False)),
                ('module', models.CharField(default=None, max_length=255)),
                ('execution_priority', models.SmallIntegerField(default=0)),
                ('document_id', models.ForeignKey(db_column='document_id', on_delete=django.db.models.deletion.PROTECT, to='docsnaps.Document', verbose_name='document')),
            ],
            options={
                'db_table': 'transform',
            },
        ),
        migrations.AddField(
            model_name='documentslanguages',
            name='language_id',
            field=models.ForeignKey(db_column='language_id', on_delete=django.db.models.deletion.PROTECT, to='docsnaps.Language', verbose_name='language'),
        ),
        migrations.AddField(
            model_name='document',
            name='languages',
            field=models.ManyToManyField(through='docsnaps.DocumentsLanguages', to='docsnaps.Language'),
        ),
        migrations.AddField(
            model_name='document',
            name='service_id',
            field=models.ForeignKey(db_column='service_id', on_delete=django.db.models.deletion.PROTECT, to='docsnaps.Service', verbose_name='service'),
        ),
        migrations.AlterUniqueTogether(
            name='transform',
            unique_together=set([('document_id', 'module')]),
        ),
        migrations.AlterIndexTogether(
            name='snapshot',
            index_together=set([('date', 'time')]),
        ),
        migrations.AlterUniqueTogether(
            name='service',
            unique_together=set([('company_id', 'name')]),
        ),
        migrations.AlterUniqueTogether(
            name='documentslanguages',
            unique_together=set([('document_id', 'language_id')]),
        ),
        migrations.AlterUniqueTogether(
            name='document',
            unique_together=set([('service_id', 'name')]),
        ),
    ]
