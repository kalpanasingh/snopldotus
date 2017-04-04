from django.db import models
from django.contrib.auth.models import User

class Institution(models.Model):
    name = models.CharField(max_length=60)
    address_line_1 = models.CharField(max_length=60)
    address_line_2 = models.CharField(max_length=60)
    address_line_3 = models.CharField(max_length=60)
    city = models.CharField(max_length=60)
    state = models.CharField(max_length=3)
    zipcode = models.CharField(max_length=6)
    secretary = models.CharField(max_length=60)
    email = models.EmailField()

    def __unicode__(self):
        return u'%s' % self.name


class UserProfile(models.Model):
    user = models.OneToOneField(User)
    institution = models.ForeignKey('Institution')
    website = models.CharField(max_length=60)
    position = models.CharField(max_length=60)

    def __unicode__(self):
        return u'%s %s (%s)' % (self.user.first_name, self.user.last_name, self.user.username)

