from django.urls import path

from . import views

urlpatterns = [
    path("", views.loginPage, name="login"),
    path("sign-up/", views.signUp, name="sign-up"),
    path("logout/", views.sign_out, name="logout")
]
