"""
Custom database router for this app.

In my experience, specialized tables and their relationships are easier to
maintain when kept outside of any one framework's or CMS' database. This
specialized data and schema is also able to be easily used in another framework
due to the absence of dependency on or relationship with Django-specific
functionality.

See:
    https://docs.djangoproject.com/en/dev/topics/db/multi-db/#automatic-database-routing

"""

APP_LABEL = 'docsnaps'
DB_NAME = 'docsnaps'

class Router:

    def db_for_read(self, model, **hints):
        read_db = None
        if model._meta.app_label == APP_LABEL:
            read_db = DB_NAME
        return read_db

    def db_for_write(self, model, **hints):
        write_db = None
        if model._meta.app_label == APP_LABEL:
            write_db = DB_NAME
        return write_db

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        allow = None
        if db == DB_NAME:
            allow = (app_label == APP_LABEL)
        elif app_label == APP_LABEL:
            allow = False
        return allow
