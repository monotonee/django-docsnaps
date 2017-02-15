# django-docsnaps
A Django application package that automates the creation of snapshots of remote documents.

This application supports the creation and maintenance of "snapshot jobs" that monitor the state of remote documents, currently only via HTTP/HTTPS. When a "snapshot job" is executed, it compares the current version of the remote document to the last snapshot and saves a new copy if the document has changed. The snapshot jobs are currently organized by company, service, and language but this may change.

A module plugin architecture is implemented that allows third-party developers to create and maintain snapshot jobs that not only specify the target documents for a snapshot job, but also provide functions to transform raw snapshots into formats more suitable for comparison, display, and storage (example: extracting relevant content from an HTML page). Maintaining separate modules for each job allows each to make use of its own Python dependencies and implement more complex document transformations.

## Installation
```bash
pip install django-docsnaps
```
Add django-docsnaps to your Django project's INSTALLED_APPS setting and then run migrations.
```bash
python manage.py migrate django-docsnaps
```
Some initial, basic data will be included in the django-docsnaps migrations such as common world languages and their ISO codes.

## Usage
The main feature provided by this Django app is a custom management command:
```bash
python manage.py docsnaps [subcommand]
```
The available subcommands will be more thoroughly documented when this app reaches a stable release. The main subcommands are currently:
* `install`: Registers a new snapshot job module with the django-docsnaps core
* `update`: Checks the specified plugin module for changes to job data and updates job registry accordingly
* `run`: Executes all active snapshot jobs
* `uninstall`: Deregisters a plugin module, removing all snapshot job data

## Currently under development
