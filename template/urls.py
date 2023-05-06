from django.urls import include, path
from template import views

urlpatterns = [

    # dashboard and list
    path("", views.dashboard, name = "template_dashboard"),
    path("list", views.list, name = "template_list"),

    # related to templates
    path("new", views.form, name = "template_new"),
    path("update/<int:pk>", views.update, name = "template_update"),
    path("delete/<int:pk>", views.delete, name = "template_delete"),
    path("duplicate<int:pk>", views.duplicate, name = "template_duplicate"),

    # related to deployment
    path("deploy/<int:pk>", views.deploy, name = "template_deploy"),
    path("stop/<int:pk>", views.stop, name = "template_stop"),
    path("delete_default/<int:pk>", views.delete_default, name = "template_delete_default"),
    path("healhcheck/<int:pk>", views.health_check, name = "template_healthcheck")

]
