"""main URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import path
from . import views


urlpatterns = [
    path('', views.homepage, name="homepage"),
    path('delete_logs/<int:pk>', views.archive_logs, name = "archive_logs"),
    path('logs/<int:pk>', views.instance_logs, name = "instance_logs"),
    path('container_logs/<int:pk>', views.container_logs, name = "container_logs"),
    path("delete_default/<int:pk>", views.delete_default, name = "delete_default"),
]
