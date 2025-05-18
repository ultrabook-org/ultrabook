import requests
import pathlib
from urllib.parse import unquote

from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.conf import settings
from django.utils.http import urlsafe_base64_decode
from .models import Project, File, Message

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, ChatOllama, OllamaLLM
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_docling import DoclingLoader
from langchain_docling.loader import ExportType
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain

embedder = OllamaEmbeddings(model="snowflake-arctic-embed2")
text_splitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=0)

OLLAMA_URL = "http://localhost:11434"  # Make sure this is set correctly

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

# Create your views here.
def home(request):
    user_projects = Project.objects.filter(user=request.user).order_by("-created_at")
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

            # Add embeddings to Chroma
            vector_store.add_documents(splits)

    return redirect(reverse('home:open-project', kwargs={"project_key": project.pk}))

def upload_file(request):
    selected_project = Project.objects.get(pk=request.POST["projectID"])

    files = request.FILES.getlist('files')
    vector_store = Chroma(
        collection_name=selected_project.title.replace(" ", "-"),
        embedding_function=embedder,
        persist_directory="./chroma_langchain_db",  # Where to save data locally, remove if not necessary
    )

    if files:
        for file in files:
            # Save file metadata
            file_instance = File(project=selected_project, file=file)
            file_instance.save()

            # Determine file type and load content
            docling_files = ('.pdf', '.docx', '.xlsx', '.pptx', '.md', '.html', '.html', '.csv')
            if file.name.endswith(docling_files):
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

            # Add embeddings to Chroma
            vector_store.add_documents(splits)
    
    return redirect(reverse('home:open-project', kwargs={"project_key": selected_project.pk}))

def open_project(request, project_key):
    try:
        selected_project = Project.objects.get(pk=project_key)
        sources = File.objects.filter(project=project_key)
        models = get_models()
        conversation = Message.objects.filter(project=selected_project).order_by('timestamp')
        source_list = []

        for source in sources:
            processed_name = source.file.name.replace("project_files/", '')
            processed_name = processed_name.replace("_", " ")
            source_list.append({
                'file': source.file,
                'processed_name': processed_name,
                'extension': processed_name.split(".")[-1],
                "file_pk": source.pk
            })

        return render(request, "ultrabook_app/project.html", {
            "project": selected_project,
            "sources": source_list,
            "models": models,
            "conversation": conversation
        })
    except Project.DoesNotExist:
        return HttpResponse("Project not found", status=404)
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)

def generate(request):
    project_id = request.POST["projectID"]
    user_prompt = request.POST["prompt"]
    
    selected_project = Project.objects.get(pk=project_id)

    vector_store = Chroma(
        collection_name=selected_project.title.replace(" ", "-"),
        embedding_function=embedder,
        persist_directory="./chroma_langchain_db", 
    )

    question_answering_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are provided multiple context items that are related to the prompt you have to answer. Use the following pieces of context to respond to the prompt at the end.\n\n{context}\n",
        ),
        ("human", "{input}"),
    ])

    llm = ChatOllama(model=selected_project.ai_model)
    combine_docs_chain = create_stuff_documents_chain(
        llm=llm,
        prompt=question_answering_prompt
    )

    retriever = vector_store.as_retriever()

    chain = create_retrieval_chain(
        retriever,
        combine_docs_chain
    )

    response = chain.invoke({"input": user_prompt})
    answer = response["answer"]
    if (answer.find("</think>") != -1):
        answer = answer.split("</think>\n")[-1]

    user_message = Message(
        project=selected_project,
        content=user_prompt,
        is_user=True,
    )

    sys_message = Message(
        project=selected_project,
        content=answer,
        is_user=False,
    )

    user_message.save()
    sys_message.save()

    return redirect(reverse('home:open-project', kwargs={"project_key": selected_project.pk}))

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

    for idx, metadata in enumerate(deletion_docs["metadatas"]):
        if metadata.get("source") == selected_file.file.name:
            ids_to_delete.append(deletion_docs["ids"][idx])

    if ids_to_delete:
        vector_store.delete(ids_to_delete)
    
    # Delete file record
    selected_file.delete()

    # Delete the file from the file system
    pathlib.Path.unlink(selected_file.file.path)
    
    return redirect(reverse('home:open-project', kwargs={"project_key": selected_project.pk}))

def switch_model(request, project_key, model_name):
    selected_project = Project.objects.get(pk=project_key)
    model_name = unquote(model_name)
    selected_project.ai_model = model_name
    selected_project.save()

    return redirect(reverse('home:open-project', kwargs={"project_key": selected_project.pk}))
