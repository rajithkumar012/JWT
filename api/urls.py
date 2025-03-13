from django.urls import path
from .views import register, login_view, logout_view, protected_view

urlpatterns = [
    path("register/", register, name="register"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("protected/", protected_view, name="protected"),
]
