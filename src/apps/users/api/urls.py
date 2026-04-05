from django.urls import path

from .views import healthcheck, jwks, login

urlpatterns = [
    path("health/", healthcheck, name="healthcheck"),
    path("auth/login/", login, name="auth-login"),
    path("auth/.well-known/jwks.json", jwks, name="auth-jwks"),
]
