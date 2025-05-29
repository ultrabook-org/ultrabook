import io
import json
import threading
import subprocess
from unittest import mock
import pytest
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from django.contrib.auth.models import User
from ultrabook_app.views import get_models, process_files, process_urls
from ultrabook_app.models import Project, File, Message
from langchain_core.documents import Document

# ------------------------
# Fixtures
# ------------------------

@pytest.fixture
def user(db):
    return User.objects.create_user(username='testuser', password='password')

@pytest.fixture
def client(user):
    client = Client()
    client.login(username='testuser', password='password')
    return client

@pytest.fixture
def project(user):
    return Project.objects.create(user=user, title='Test', desc='desc', ai_model='model')

# ------------------------
# Test get_models
# ------------------------

def test_get_models_success(monkeypatch):
    mock_response = mock.Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {'models': [{'model': 'a'}, {'model': 'b'}]}
    monkeypatch.setattr('requests.get', lambda url: mock_response)
    models = get_models()
    assert models == ['a', 'b']


def test_get_models_failure(monkeypatch):
    monkeypatch.setattr('requests.get', lambda url: (_ for _ in ()).throw(Exception("fail")))
    models = get_models()
    assert models == []

# ------------------------
# Test process_files and process_urls
# ------------------------

class DummyStore:
    def __init__(self):
        self.added = []
    def add_documents(self, docs):
        self.added.extend(docs)

class DummyDoc:
    def __init__(self, content, id):
        self.page_content = content
        self.id = id

class DummyLoader:
    def __init__(self, docs): self.docs = docs
    def load(self): return self.docs

class DummyURLLoader(DummyLoader): pass

@override_settings(MEDIA_ROOT='/tmp')
def test_process_files(tmp_path, project, monkeypatch):
    # Create a dummy file
    file_content = b"hello world"
    file = SimpleUploadedFile("test.md", file_content)
    # Patch DoclingLoader and text_splitter
    dummy_docs = [DummyDoc("content1", "id1"), DummyDoc("content2", "id2")]
    monkeypatch.setattr('ultrabook_app.views.DoclingLoader', lambda file_path, export_type: DummyLoader(dummy_docs))
    dummy_store = DummyStore()
    process_files([file], dummy_store, project)
    # After processing, documents from dummy_docs should be split and added
    assert dummy_store.added

@override_settings(MEDIA_ROOT='/tmp')
def test_process_urls(monkeypatch, project):
    url = "http://example.com"
    dummy_docs = [DummyDoc("page1", "u1")]
    monkeypatch.setattr('ultrabook_app.views.SeleniumURLLoader', lambda urls: DummyURLLoader(dummy_docs))
    dummy_store = DummyStore()
    process_urls([url], dummy_store, project)
    assert dummy_store.added

# ------------------------
# Test views
# ------------------------

def test_home_view(client, project):
    response = client.get(reverse('home:home'))
    assert response.status_code == 200
    assert b'Test' in response.content

@override_settings(OLLAMA_BASE_URL='http://ollama')
@mock.patch('ultrabook_app.views.process_files')
@mock.patch('ultrabook_app.views.process_urls')
def test_new_project_view(mock_urls, mock_files, client):
    data = {'title': 'New', 'desc': 'Desc', 'urls': ''}
    response = client.post(reverse('home:new_project'), data)
    # Should redirect to open-project
    assert response.status_code == 302

@mock.patch('ultrabook_app.views.Chroma')
@mock.patch('ultrabook_app.views.process_files')
@mock.patch('ultrabook_app.views.process_urls')
def test_upload_file_view(mock_urls, mock_files, mock_chroma, client, project):
    file = SimpleUploadedFile("f.txt", b"data")
    data = {'projectID': project.pk, 'urls': ''}
    response = client.post(reverse('home:upload_file'), data, files={'files': file})
    assert response.status_code == 302


def test_open_project_not_found(client):
    response = client.get(reverse('home:open-project', kwargs={'project_key': 999}))
    assert response.status_code == 404

@mock.patch('ultrabook_app.views.ChatOllama')
@mock.patch('ultrabook_app.views.create_retrieval_chain')
@mock.patch('ultrabook_app.views.create_stuff_documents_chain')
@mock.patch('ultrabook_app.views.Chroma')
def test_generate_stream_view(mock_chroma, mock_stuff_chain, mock_retrieval_chain, mock_llm, client, project):
    # Mock chain.stream
    dummy_chain = mock.Mock()
    dummy_chain.stream.return_value = [ {'answer': 'hi'} ]
    mock_retrieval_chain.return_value = dummy_chain
    response = client.post(reverse('home:generate_stream'), {'projectID': project.pk, 'prompt': 'hello'})
    assert response.status_code == 200
    assert response.streaming

@mock.patch('ultrabook_app.views.Chroma')
def test_delete_source_view(mock_chroma, client, project):
    # Create a file record
    f = File.objects.create(project=project, url='http://x')
    # Mock get metadatas and ids
    mock_store = mock.Mock()
    mock_store.get.return_value = {'metadatas': [{'source': 'http://x'}], 'ids': ['id1']}
    mock_chroma.return_value = mock_store
    response = client.post(reverse('home:delete_source', kwargs={'project_key': project.pk, 'file_key': f.pk}))
    assert response.status_code == 302

@mock.patch('ultrabook_app.views.Project')
def test_switch_model_view(mock_project, client):
    mock_obj = mock.Mock()
    mock_project.objects.get.return_value = mock_obj
    response = client.get(reverse('home:switch-model', kwargs={'project_key': 1, 'model_name': 'mymodel'}))
    assert response.status_code == 302

@mock.patch('ultrabook_app.views.subprocess')
@mock.patch('ultrabook_app.views.Project')
def test_fetch_model_view_success(mock_project, mock_subproc, client):
    mock_obj = mock.Mock(pk=1)
    mock_project.objects.get.return_value = mock_obj
    response = client.post(reverse('home:fetch_model'), {'projectID': 1, 'model': 'm'})
    assert response.status_code == 302

@mock.patch('ultrabook_app.views.subprocess')
@mock.patch('ultrabook_app.views.Project')
def test_fetch_model_view_failure(mock_project, mock_subproc, client):
    mock_obj = mock.Mock(pk=1)
    mock_project.objects.get.return_value = mock_obj
    mock_subproc.run.side_effect = subprocess.CalledProcessError(1, 'ollama')
    response = client.post(reverse('home:fetch_model'), {'projectID': 1, 'model': 'm'})
    assert response.status_code == 302

@mock.patch('ultrabook_app.views.Project')
def test_delete_project_view(mock_project, client):
    mock_obj = mock.Mock()
    mock_project.objects.get.return_value = mock_obj
    response = client.post(reverse('home:delete-project', kwargs={'project_key': 1}))
    assert response.status_code == 302


def test_save_message_missing_fields(client):
    response = client.post(reverse('home:save_message'), {})
    assert response.status_code == 400

@pytest.mark.django_db
def test_save_message_success(client, project):
    response = client.post(reverse('home:save_message'), {'project_id': project.pk, 'message': 'msg', 'is_user': 'true'})
    assert response.status_code == 302
    assert Message.objects.filter(project=project, content='msg', is_user=True).exists()
