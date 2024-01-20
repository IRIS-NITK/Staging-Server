from django.urls import path
from django.views.decorators.http import require_POST
from repositories import views

urlpatterns = [
    path('', views.index, name='repositories_dashboard'),
    path('create/', require_POST(views.create), name='repositories_create'),
    path("view/<int:pk>", views.repository_dashboard, name = "repositories_repository_dashboard"),
    path("update/<int:pk>", views.update_repository, name = "repositories_update_repository"),
    path("deploy/<int:pk>", views.deploy, name = "repositories_deploy_branch"),
]