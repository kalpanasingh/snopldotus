from django.contrib import admin
from snopldotus.models import Institution, UserProfile
from detector.models import Subsystem, Tag

admin.site.register(Institution)
admin.site.register(UserProfile)
admin.site.register(Subsystem)
admin.site.register(Tag)

