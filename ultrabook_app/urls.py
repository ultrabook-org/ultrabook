from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("new-project/", views.new_project, name="new-project")
]