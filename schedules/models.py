from django.db import models

import os.path

class Schedule(models.Model):
    UPLOAD_PATH = 'schedules/%Y/%m'

    start_date = models.DateField()
    end_date = models.DateField()
    notes = models.CharField(max_length=1000, blank=True)
    docfile = models.FileField(upload_to=os.path.join('static', UPLOAD_PATH))

    def filename(self):
        return os.path.basename(self.docfile.name)

    def filepath(self):
        return self.docfile.name[len('static/'):]

