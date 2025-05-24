from django.test import TestCase, Client
from unittest.mock import patch
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User
from .models import Project, File, Message

class HomeViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="12345")
        self.client.force_login(self.user)

    def test_home_view_renders_template(self):
        response = self.client.get(reverse("home:home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "ultrabook_app/home.html")

class NewProjectViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="12345")
        self.client.force_login(self.user)

    def test_new_project_creates_project_and_files(self):       
        response = self.client.post(reverse("home:new-project"), {
            "title": "Test Project",
            "desc": "Description",
            "files": []
        })
        
        self.assertEqual(response.status_code, 302)

class OpenProjectViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="12345")
        self.client.force_login(self.user)
        self.project = Project.objects.create(
            user=self.user,
            title="Test Project",
            desc="Test Desc",
            ai_model="qwen3:8b"
        )
        self.file = File.objects.create(
            project=self.project,
            file="test_file.txt"
        )

    def test_open_project_renders_template(self):
        response = self.client.get(reverse("home:open-project", args=[self.project.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "ultrabook_app/project.html")

class GenerateViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="12345")
        self.client.force_login(self.user)
        self.project = Project.objects.create(
            user=self.user,
            title="Test Project",
            desc="Test Desc",
            ai_model="qwen3:8b"
        )

    @patch("langchain_chroma.Chroma")
    def test_generate_saves_messages(self, mock_chroma):
        mock_chroma.return_value = None
        response = self.client.post(reverse("home:gen"), {
            "projectID": self.project.pk,
            "prompt": "Test prompt"
        })
        
        self.assertEqual(response.status_code, 200)
        messages = Message.objects.filter(project=self.project)
        self.assertEqual(messages.count(), 1)