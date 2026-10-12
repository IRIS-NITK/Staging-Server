from django.urls import path
from django.views.decorators.http import require_POST
from github_social import views

urlpatterns = [
    path('deploy/<int:pk>', require_POST(views.deploy), name='github_social_deploy'),
    path('healhcheck/<int:pk>', views.health_check, name='github_social_healthcheck'),
    path('stop_with_db/<int:pk>', views.stop_with_db, name='github_social_stop_with_db'),
    path('stop/<int:pk>', views.stop, name='github_social_stop'),
    path('delete/<int:pk>', require_POST(views.delete), name='github_social_delete'),
    path('get_projects/', views.get_projects, name='github_get_projects'),
    path('get_branches/', views.get_branches, name='github_get_branches'),
    path('', views.index, name='github_social_dashboard'),
]
