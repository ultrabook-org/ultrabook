from django.db import models
from django.contrib.auth.models import User
from django.db.models.functions import Now

class Project(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    desc = models.TextField()
    icon = models.TextField(db_default="stars")
    created_at = models.DateTimeField(db_default=Now())
    ai_model = models.CharField(max_length=100)

    def __str__(self):
        return self.title

class File(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    file = models.FileField(upload_to='project_files/')
    uploaded_at = models.DateTimeField(db_default=Now())
    url = models.TextField()

    def __str__(self):
        return f"File {self.file.name} for {self.project.title}"

class Message(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    content = models.TextField()
    is_user = models.BooleanField(db_default=True)
    timestamp = models.DateTimeField(db_default=Now())

    def __str__(self):
        return f"{'User' if self.is_user else 'AI'}: {self.content[:20]}"
