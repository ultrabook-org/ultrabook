import requests
import pathlib
import subprocess
import json
import threading
import tempfile
import os
import string
from urllib.parse import unquote

from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.http import StreamingHttpResponse, JsonResponse
from django.views.decorators.cache import never_cache
from django.conf import settings
from django.core.files.base import ContentFile
from .models import Project, File, Message, Podcast

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_docling import DoclingLoader
from langchain_docling.loader import ExportType
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from langchain_community.document_loaders import SeleniumURLLoader

from dia.model import Dia
import torch
from RealtimeTTS import TextToAudioStream, KokoroEngine

embedder = OllamaEmbeddings(model="snowflake-arctic-embed2")
text_splitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=0)

OLLAMA_URL = settings.OLLAMA_BASE_URL  # Make sure this is set correctly

def get_models() -> list:
    try:
        thelist = requests.get(OLLAMA_URL + "/api/tags")
        thelist.raise_for_status()  # Ensure we handle HTTP errors
        jsondata = thelist.json()
        result = []
        for model in jsondata["models"]:
            result.append(model["model"])
        return result
    except Exception as e:
        # Optionally log or handle errors
        return []

def process_files(files, vector_store, project):
    threads = []
    for file in files:
        thread = threading.Thread(target=_process_file, args=(file, vector_store, project))
        threads.append(thread)
        thread.start()
    for thread in threads:
        thread.join()

def _process_file(file, vector_store, project):
    file_instance = File(project=project, file=file)
    file_instance.save()

    if file_instance.file.name.endswith(('.pdf', '.docx', '.xlsx', '.pptx', '.md', '.html', '.csv', '.png', '.jpeg', '.tiff', '.bmp', '.webp')):
        loader = DoclingLoader(
            file_path=file_instance.file.path,
            export_type=ExportType.DOC_CHUNKS
        )
    else:
        loader = None

    documents = loader.load() if loader else []
    filtered_documents = []
    for doc in documents:
        filtered_documents.append(
            Document(
                page_content=doc.page_content,
                id=doc.id,
                metadata={"source": file_instance.file.name}
            )
        )

    splits = text_splitter.split_documents(filtered_documents)
    vector_store.add_documents(splits)

def process_urls(urls, vector_store, project):
    threads = []
    for url in urls:
        thread = threading.Thread(target=_process_url, args=(url, vector_store, project))
        threads.append(thread)
        thread.start()
    for thread in threads:
        thread.join()

def _process_url(url, vector_store, project):
    url_file_instance = File(project=project, url=url)
    url_file_instance.save()

    loader = SeleniumURLLoader(urls=[url])
    documents = loader.load()

    filtered_documents = []
    for doc in documents:
        filtered_documents.append(
            Document(
                page_content=doc.page_content,
                id=doc.id,
                metadata={"source": url}
            )
        )

    splits = text_splitter.split_documents(filtered_documents)
    vector_store.add_documents(splits)

# Create your views here.
@login_required
def home(request):
    user_projects = Project.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "ultrabook_app/home.html", {
        "projects": user_projects
    })

@login_required
def new_project(request):
    try:
        project = Project(
            user=request.user,
            title=request.POST["title"],
            desc=request.POST["desc"],
            ai_model=settings.DEFAULT_MODEL
        )
        project.save()
    except Exception as e:
        print(f"Failed to create project: {e}")

    vector_store = Chroma(
        collection_name=request.POST["title"].replace(" ", "-"),
        embedding_function=embedder,
        persist_directory="./chroma_langchain_db",
    )

    files = request.FILES.getlist('files')
    urls = request.POST['urls']

    thread1 = threading.Thread(target=process_files, args=(files, vector_store, project))
    thread1.start()

    thread2 = None
    if urls:
        thread2 = threading.Thread(target=process_urls, args=(urls.split(','), vector_store, project))
        thread2.start()

    # Wait for both threads to complete
    thread1.join()
    if urls:
        thread2.join()

    return redirect(reverse('home:open-project', kwargs={"project_key": project.pk}))

@login_required
def upload_file(request):
    selected_project = Project.objects.get(pk=request.POST["projectID"])

    vector_store = Chroma(
        collection_name=selected_project.title.replace(" ", "-"),
        embedding_function=embedder,
        persist_directory="./chroma_langchain_db",
    )

    files = request.FILES.getlist('files')
    urls = request.POST['urls']

    thread1 = threading.Thread(target=process_files, args=(files, vector_store, selected_project))
    thread1.start()

    thread2 = None
    if urls:
        thread2 = threading.Thread(target=process_urls, args=(urls.split(','), vector_store, selected_project))
        thread2.start()

    # Wait for both threads to complete
    thread1.join()
    if urls:
        thread2.join()

    return redirect(reverse('home:open-project', kwargs={"project_key": selected_project.pk}))

@login_required
def open_project(request, project_key, **kwargs):
    try:
        selected_project = Project.objects.get(pk=project_key)
        sources = File.objects.filter(project=project_key)
        models = get_models()
        conversation = Message.objects.filter(project=selected_project).order_by('timestamp')
        source_list = []

        for source in sources:
            processed_name = source.file.name.replace("project_files/", '') if source.file else source.url
            processed_name = processed_name.replace("_", " ")
            is_url = True if source.url else False
            source_list.append({
                'file': source.file,
                'processed_name': processed_name,
                'extension': processed_name.split(".")[-1],
                "file_pk": source.pk,
                "is_url": is_url
            })
        
        podcast = None
        if Podcast.objects.filter(project=selected_project).exists():
            podcast = Podcast.objects.get(project=selected_project)

        return render(request, "ultrabook_app/project.html", {
            "project": selected_project,
            "sources": source_list,
            "models": models,
            "conversation": conversation,
            "error_message": kwargs.get("error_message", None),
            "podcast_file": podcast.file.url if podcast else None
        })
    except Project.DoesNotExist:
        return HttpResponse("Project not found", status=404)
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)
    
@login_required
def generate_stream(request):
    project_id = request.POST['projectID']
    user_prompt = request.POST['prompt']
    selected_project = Project.objects.get(pk=project_id)

    # Prepare vector store & chain
    vector_store = Chroma(
        collection_name=selected_project.title.replace(' ', '-'),
        embedding_function=embedder,
        persist_directory='./chroma_langchain_db',
    )
    prompt_template = ChatPromptTemplate.from_messages([
        MessagesPlaceholder(variable_name="chat_history"),
        ('system', 'Use the context to answer:\n\n{context}\n'),
        ('human', '{input}'),
    ])
    llm = ChatOllama(model=selected_project.ai_model)
    combine_chain = create_stuff_documents_chain(llm=llm, prompt=prompt_template)
    retriever = vector_store.as_retriever()
    chain = create_retrieval_chain(retriever, combine_chain)


    messages = Message.objects.filter(project=selected_project).values('content', 'is_user')
    chat_history = chat_history = [
        {
            'content': msg['content'],
            'role': 'human' if msg['is_user'] else 'ai'
        }
        for msg in messages
    ]
    
    # Save user message immediately
    usr_msg = Message.objects.create(
        project=selected_project,
        content=user_prompt,
        is_user=True,
    )
    
    usr_msg.save()

    def stream_generator():
        for chunk in chain.stream({
            'input': user_prompt,
            'chat_history': chat_history
        }):
            text = chunk.get('answer', '')
            if text:
                yield f"data: {json.dumps({'chunk': text})}\n\n"

    response = StreamingHttpResponse(
        stream_generator(),
        content_type='text/event-stream'
    )

    response['Cache-Control'] = 'no-cache'
    return response


@login_required
def delete_source(request, project_key, file_key):
    selected_project = Project.objects.get(pk=project_key)
    selected_file = File.objects.get(pk=file_key)
    
    # Initialize Chroma vector store
    vector_store = Chroma(
        collection_name=selected_project.title.replace(" ", "-"),
        embedding_function=embedder,
        persist_directory="./chroma_langchain_db",
    )

    ids_to_delete = []
    deletion_docs = vector_store.get(include=["metadatas"])

    if selected_file.file:
        for idx, metadata in enumerate(deletion_docs["metadatas"]):
            if metadata.get("source") == selected_file.file.name:
                ids_to_delete.append(deletion_docs["ids"][idx])

        if ids_to_delete:
            vector_store.delete(ids_to_delete)
        
        # Delete file record
        selected_file.delete()

        # Delete the file from the file system
        pathlib.Path.unlink(selected_file.file.path)
    else:
        for idx, metadata in enumerate(deletion_docs["metadatas"]):
            if metadata.get("source") == selected_file.url:
                ids_to_delete.append(deletion_docs["ids"][idx])

        if ids_to_delete:
            vector_store.delete(ids_to_delete)

        selected_file.delete()        
    
    return redirect(reverse('home:open-project', kwargs={"project_key": selected_project.pk}))

@login_required
def switch_model(request, project_key, model_name):
    selected_project = Project.objects.get(pk=project_key)
    model_name = unquote(model_name)
    selected_project.ai_model = model_name
    selected_project.save()

    return redirect(reverse('home:open-project', kwargs={"project_key": selected_project.pk}))

@login_required
def fetch_model(request):
    project_key = request.POST["projectID"]
    selected_project = Project.objects.get(pk=project_key)

    model_name = unquote(request.POST["model"])
    
    try:
        subprocess.run(["ollama", "pull", model_name], check=True)
        selected_project.ai_model = model_name
        selected_project.save()
    except subprocess.CalledProcessError as e:
        error_message = f"Failed to pull model '{model_name}': {e}"
        return redirect(reverse('home:open-project', kwargs={"project_key": selected_project.pk, "error_message": error_message}))

    return redirect(reverse('home:open-project', kwargs={"project_key": selected_project.pk}))

@login_required
def delete_project(request, project_key):
    selected_project = Project.objects.get(pk=project_key)
    selected_project.delete()

    return redirect("/home")

@login_required
def save_message(request):
    if request.method == 'POST':
        # Extract the project ID and message from the POST data
        project_id = request.POST.get('project_id')
        system_message = request.POST.get('message')
        is_user = request.POST.get('is_user', 'false') == 'true'

        if not project_id or not system_message:
            return JsonResponse({'error': 'Missing project_id or message'}, status=400)

        try:
            project = Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return JsonResponse({'error': 'Project not found'}, status=404)

        # Save the system message
        msg = Message.objects.create(
            project=project,
            content=system_message,
            is_user=is_user,
        )

        msg.save()

        return redirect(reverse('home:open-project', kwargs={"project_key": project_id}))
    
    else:
        return redirect('home/')

def text_to_audio(request):
    project = get_object_or_404(Project, pk=request.POST["projectID"])

    vector_store = Chroma(
        collection_name=project.title.replace(' ', '-'),
        embedding_function=embedder,
        persist_directory='./chroma_langchain_db',
    )
    prompt_template = ChatPromptTemplate.from_messages([
        MessagesPlaceholder(variable_name="chat_history"),
        ('system', """
You are a professional podcast host. You are on a live show with the provided context and conversation from before. You play the role of 'Ava' (a helpful research, learning and planning assistant) and
         must give a speech on the chat history as well as the context. Get straight into the dialogue and do not use any special characters or 
         markdown syntax. Feel free to introduce yourself or welcome viewers to the show but do not make any reference to hosts, guests or music/background sounds. Be as detailed and accurate as possible, discussing the context to generate a long script. Here is the context:\n{context}
"""),
        ('human', '{input}'),
    ])
    try:
        llm = ChatOllama(model=settings.PODCAST_MODEL)
    except:
        try:
            process = subprocess.run(["ollama", "pull", settings.PODCAST_MODEL], check=True)
            process.wait()
            llm = ChatOllama(model=settings.PODCAST_MODEL)
        except:
            print("Unable to generate podcast with selected model")
            return redirect(reverse('home:open-project', kwargs={"project_key": project.pk}))

    combine_chain = create_stuff_documents_chain(llm=llm, prompt=prompt_template)
    retriever = vector_store.as_retriever()
    chain = create_retrieval_chain(retriever, combine_chain)

    messages = Message.objects.filter(project=project).values('content', 'is_user')
    chat_history = [
        {
            'content': msg['content'],
            'role': 'human' if msg['is_user'] else 'ai'
        }
        for msg in messages
    ]

    engine = KokoroEngine()
    stream = TextToAudioStream(
        engine=engine,
    )
    
    for chunk in chain.stream({
                "input": "Create a podcast using all the documents available to you.",
                'chat_history': chat_history
            }):
                text = chunk.get('answer', '')
                if text:
                    stream.feed(text)

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    stream.play(output_wavfile=tmp.name)
    tmp.flush()

    sanitized_name = project.title.translate(str.maketrans('', '', string.punctuation))
    with open(tmp.name, 'rb') as f:
        podcast_instance = Podcast(project=project)
        podcast_instance.file.save(f"audio_{sanitized_name}.mp3", f)
        podcast_instance.save()
    
    return redirect(reverse('home:open-project', kwargs={"project_key": project.pk}))