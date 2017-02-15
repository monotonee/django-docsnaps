Django Document Snapshots
=========================
A Django application that is designed track changes in documents.

The primary utility is the provision of a custom management command. When run,
the command checks each active document, compares it with its most recent
snapshot if any exist and, if a change is detected, saves a new snapshot. Over
time, a tracable series of changes to a document are recorded. The management
command can be run from a cron job, systemd timer, or any other task scheduler.
