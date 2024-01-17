from django.urls import path
from django.views.decorators.http import require_POST
from gitlab_social import views

urlpatterns = [
  
    # related to deployment
    path('deploy/<int:pk>', require_POST(views.deploy), name='gitlab_social_deploy'),
    path("healhcheck/<int:pk>", views.health_check, name = "gitlab_social_healthcheck"),
    path("stop_with_db/<int:pk>", views.stop_with_db, name = "gitlab_social_stop_with_db"),
    path("stop/<int:pk>", views.stop, name = "gitlab_social_stop"),
    path('', views.index, name='gitlab_social_dashboard'),
    path('get_projects/', views.get_projects, name='get_projects'),
    path('get_branches/', views.get_branches, name='get_branches'),

    # TO DO : logs , container logs, attach portainer, 
]