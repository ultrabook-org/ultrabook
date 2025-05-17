from django.shortcuts import render, redirect
from django.urls import reverse
from .models import Project, File

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_docling import DoclingLoader
from langchain_docling.loader import ExportType
from langchain_community.vectorstores.utils import filter_complex_metadata
from langchain_core.documents import Document

from docling.chunking import HybridChunker

embedder = OllamaEmbeddings(model="snowflake-arctic-embed2")
text_splitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=0)

# Create your views here.
def home(request):
    user_projects = Project.objects.filter(user=request.user)
    return render(request, "ultrabook_app/home.html", {
        "projects": user_projects
    })

def new_project(request):
    try:
        project = Project(
            user=request.user, 
            title=request.POST["title"], 
            desc=request.POST["desc"], 
            ai_model="qwen3:8b"
        )

        project.save()
    except Exception as e:
        print(f"Failed to create project: {e}")

    files = request.FILES.getlist('files')
    vector_store = Chroma(
        collection_name=request.POST["title"].replace(" ", "-"),
        embedding_function=embedder,
        persist_directory="./chroma_langchain_db",  # Where to save data locally, remove if not necessary
    )

    if files:
        for file in files:
            # Save file metadata
            file_instance = File(project=project, file=file)
            file_instance.save()

            # Determine file type and load content
            docling_files = ('.pdf', '.docx', '.xlsx', '.pptx', '.md', '.html', '.html', '.csv')
            if file.name.endswith(docling_files):
                loader = DoclingLoader(
                    file_path=file_instance.file.path,
                    export_type=ExportType.DOC_CHUNKS
                )
            else:
                loader = None  # Handle other formats or skip

            documents = loader.load() if loader else []

            filtered_documents = []
            for doc in documents:
                filtered_documents.append(Document(
                    page_content=doc.page_content,
                    id=doc.id,
                    metadata={}
                ))

            splits = text_splitter.split_documents(filtered_documents)

            # Add embeddings to Chroma
            vector_store.add_documents(splits)

    return redirect(reverse('home:home'))

def upload_file(request, project_key):
    return redirect(reverse('home:home'))

def open_project(request, project_key):
    selected_project = Project.objects.filter(pk=project_key)
    return render(request, "ultrabook_app/project.html", {
        "project": selected_project
    })