from django.urls import include, path
from template import views

urlpatterns = [

    # dashboard and list
    path("", views.dashboard, "template_dashboard"),
    path("list", views.list, "template_list"),

    # related to templates
    path("new", views.form, "template_new"),
    path("update/<int:pk>", views.update, "template_update"),
    path("delete/<int:pk>", views.delete, "template_delete"),
    path("duplicate<int:pk>", views.duplicate, "template_duplicate"),

    # related to deployment
    path("deploy/<int:pk>", views.deploy, "template_deploy"),
    path("stop/<int:pk>", views.stop, "template_stop"),

]
