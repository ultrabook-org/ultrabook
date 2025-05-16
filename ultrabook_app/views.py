from django.shortcuts import render, redirect
from django.urls import reverse
from django.db import models
from .models import Project

# Create your views here.
def home(request):
    user_projects = Project.objects.filter(user=request.user)
    return render(request, "ultrabook_app/home.html", {
        "projects": user_projects
    })

def new_project(request):
    try: 
        project = Project(user=request.user, title=request.POST["title"], desc=request.POST["desc"], ai_model="qwen3:8b")
        project.save()
    except:
        print("Failed to create project")

    return redirect(reverse('home:home'))