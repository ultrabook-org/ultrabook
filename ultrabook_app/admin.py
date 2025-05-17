from django.contrib import admin
from .models import Project, File, Message

admin.site.register(Project)
admin.site.register(File)
admin.site.register(Message)
