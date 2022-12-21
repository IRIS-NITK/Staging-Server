from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from allauth.socialaccount.models import SocialToken
from github import Github
import gitlab,json
from django.http import HttpResponse
from django.core.paginator import Paginator

# Create your views here.
@login_required(login_url='/accounts/login/')
def home(response):
    # Example of how to get the access token for a particular provider
    # PyGithub: https://pygithub.readthedocs.io/en/latest/introduction.html
    gh_access_token_set = SocialToken.objects.filter(account__user=response.user, account__provider='github')
    if (len(gh_access_token_set) == 0):
        print("No Github Access Token")
    else:
        g = Github(gh_access_token_set.first().__str__())
        print("1", g.get_user().login)
        for repo in g.get_user().get_orgs():
                print(repo.name)

    gl_access_token_set = SocialToken.objects.filter(account__user=response.user, account__provider='gitlab')
    if (len(gl_access_token_set) == 0):
        print("No Gitlab Access Token")
    else:
        # Python Gitlab: https://python-gitlab.readthedocs.io/en/stable/
        gl = gitlab.Gitlab(url='https://git.iris.nitk.ac.in', oauth_token=gl_access_token_set.first().__str__())
        gl.auth()
        print("2", gl.user.emails.list())
    return render(response, "main/home.html")

@login_required(login_url='/accounts/login/')
def form(request):

    gh_access_token_set = SocialToken.objects.filter(account__user=request.user, account__provider='github')
    g = Github(gh_access_token_set.first().__str__())
    name = g.get_user().login
    o = list(g.get_user().get_orgs())
    orgs_name = {}
    val = 2
    orgs_name[1] = g.get_user().login
    for i in o:
        orgs_name[val] = i.name
        val+=1

    return render(request,'form.html',{'orgs_name':orgs_name})

@login_required(login_url='/accounts/login/')
def getrepos(request):
    gh_access_token_set = SocialToken.objects.filter(account__user=request.user, account__provider='github')
    g = Github(gh_access_token_set.first().__str__())
    o = list(g.get_user().get_orgs())

    organisation = request.GET.get('org')
    repos={}
    val=1
    obj=""

    if organisation == g.get_user().login:
        for i in g.get_user().get_repos():
            repos[val]=i.name
            val+=1
    else:
        for i in o:
            if i.name == organisation:
                obj=i 
                break
        for i in obj.get_repos():
            repos[val] = i.name
            val+=1
            
    return render(request,'response.html',{'repos':repos})

