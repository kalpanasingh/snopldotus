from django.db import models
from snopldotus.models import UserProfile

class Subsystem(models.Model):
    name = models.CharField(max_length=250)
    description = models.CharField(max_length=1000)
    contact = models.ForeignKey(UserProfile)
    enabled = models.BooleanField(default=False)
    problems = models.BooleanField(default=False)

    def __unicode__(self):
        return u'%s' % (self.name)


class Tag(models.Model):
    STATUS_CHOICES = (
        ('default', 'None'),
        ('success', 'Good'),
        ('warning', 'Has problems'),
        ('danger', 'Bad'),
    )
    subsystem = models.ForeignKey(Subsystem)
    author = models.ForeignKey(UserProfile)
    message = models.TextField()
    status = models.CharField(max_length=8, choices=STATUS_CHOICES, default='default')
    timestamp = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return '%s... (%s, %s)' % (str(self.message)[:15], self.author, self.timestamp)

