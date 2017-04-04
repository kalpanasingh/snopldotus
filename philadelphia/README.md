Philadelphia Django Client
==========================
A Django front-end for Philadelphia shift reports. This allows administrators
to hide the CouchDB database from the user, allowing document-level security
(for example, users cannot delete submitted reports).

Settings
--------
Add the following to the Django application settings:

    PHILA_SERVER = Philadelphia DB server (e.g. 'localhost:5984')
    PHILA_AUTH = Philadelphia DB authentication string (e.g. 'user:pass')
    PHILA_TZ = Time zone for display (e.g. 'America/New_York')
    PHILA_EMAIL_LIST = Notification list for submitted reports (e.g. ['foo@example.com'])
    PHILA_SMTP_SERVER = SMTP server for sending email notifications (e.g. 'localhost')

