from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.urls import reverse

def loginPage(request):
    if request.method == 'GET':
        return render(request, "users/login.html")
    if request.method == 'POST':
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect(reverse('home:home'))
        else:
            return render(request, "users/login.html", {
                "error_message": "Invalid email or password"
            })

def signUp(request):
    if request.method == 'GET':
        return render(request, "users/sign-up.html")
    if request.method == 'POST':
        username = request.POST["username"]
        password = request.POST["password"]
        confPassword = request.POST["confirmPassword"]

        if password == confPassword:
            try:
                user = User.objects.create_user(username=username, password=password)
                login(request, user)
                return redirect(reverse('home:home'))
            except:
                return render(request, "users/sign-up.html", {
                    "error_message": "Error creating account"
                })
        else:
            return render(request, "users/sign-up.html", {
                "error_message": "Passwords do not match"
            })
        
def sign_out(request):
    if request.user.is_authenticated:
        logout(request)
        return redirect(reverse("users:login"))