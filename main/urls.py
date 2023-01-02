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
    path('', views.home, name="home"),
    path('form_wrapper',views.form_wrapper,name="form_wrap"),
    path('form/<social>',views.form,name="form"),
    path('getrepos',views.getrepos,name="repos"),
    path('getbranches',views.getbranches,name="branches"),
    path('getIRISbranches',views.getIRISbranches,name="IRISbranches"),
    path('deploy',views.deploy_wrapper,name="deploy_wrap"),
    path("containerlogs/<orgname>/<reponame>/<branch>/<social>",views.getcontainerlogs,name="containerlogs"),
    path("logs/<orgname>/<reponame>/<branch>/<social>",views.logs,name="logs"),
    path('deploy/<org_name>/<repo_name>/<branch>/<social>',views.deploy,name="deploy"),
    path('stop/<social>/<orgname>/<reponame>/<branch>',views.stop,name='stop'),
]
