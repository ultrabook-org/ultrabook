from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("new-project/", views.new_project, name="new-project"),
    path("open-project/<int:project_key>/", views.open_project, name="open-project"),
    path("upload-file/", views.upload_file, name="upload-file"),
    path("gen/", views.generate_stream, name="gen"),
    path("delete-source/<int:project_key>/<int:file_key>/", views.delete_source, name="delete-source"),
    path("delete-project/<int:project_key>/", views.delete_project, name="delete-project"),
    path("switch-model/<int:project_key>/<str:model_name>/", views.switch_model, name="switch-model"),
    path("get-model/", views.fetch_model, name="get-model"),
    path("save-system-message/", views.save_message, name='save-system-message'),
    path("create-podcast/", views.text_to_audio, name="create-podcast")
]

if settings.DEBUG:
  urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)