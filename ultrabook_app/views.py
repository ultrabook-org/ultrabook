from django.shortcuts import render, redirect
from django.urls import reverse
from .models import Project, File

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
    if files:
        for file in files:
            file_instance = File(project=project, file=file)
            file_instance.save()

    return redirect(reverse('home:home'))

def upload_file(request, project_key):
    return redirect(reverse('home:home'))

def open_project(request, project_key):
    selected_project = Project.objects.filter(pk=project_key)
    return render(request, "ultrabook_app/project.html", {
        "project": selected_project
    })