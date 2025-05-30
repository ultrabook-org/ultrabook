from django.contrib import admin
from .models import Project, File, Message, Podcast

admin.site.register(Project)
admin.site.register(File)
admin.site.register(Message)
admin.site.register(Podcast)