from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from allauth.socialaccount.models import SocialToken
from github import Github
import gitlab,json
from django.http import HttpResponse
from django.shortcuts import render,redirect
from main.tasks.services import deploy_from_git
from django.core import serializers
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
        try:
            gl.auth()
        except:
            return redirect("socialaccount_connections")
        print("2", gl.user.emails.list())
    return render(response, "main/home.html")


@login_required(login_url='/accounts/login/')
def form_wrapper(request):

    social = request.POST.get('social')
    if(social == "Github"):
        gh_access_token_set = SocialToken.objects.filter(account__user=request.user, account__provider='github')
        if (len(gh_access_token_set) == 0):
            return redirect("socialaccount_connections")
        else:
            return redirect("form",social)
    else:
        gl_access_token_set = SocialToken.objects.filter(account__user=request.user, account__provider='gitlab')
        if (len(gl_access_token_set) == 0):
            return redirect("socialaccount_connections")
        else:
            return redirect("form",social)


@login_required(login_url='/accounts/login/')
def form(request,social):

    account__provider = social
    

    if social == "Github":
        gh_access_token_set = SocialToken.objects.filter(account__user=request.user, account__provider='github')
        g = Github(gh_access_token_set.first().__str__())
        name = g.get_user().login
        o = list(g.get_user().get_orgs())
        val = 2
        orgs_name = {}
        orgs_name[1] = g.get_user().login
        for i in o:
            orgs_name[val] = i.name
            val+=1
        return render(request,'form.html',{'orgs_name':orgs_name})
    else:
        gl_access_token_set = SocialToken.objects.filter(account__user=request.user, account__provider='gitlab')
        gl = gitlab.Gitlab(url='https://git.iris.nitk.ac.in', oauth_token=gl_access_token_set.first().__str__())
        gl.auth()
        projects = gl.projects.list(get_all=True)
        repos = {}
        val = 1
        for i in projects:
            repos[val] = i.name
            val+=1
        return render(request,'gitlabform.html',{'repos':repos})
    
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

    return render(request,'response.html',{'dictionary':repos})

@login_required(login_url='/accounts/login/')
def getbranches(request):

    gh_access_token_set = SocialToken.objects.filter(account__user=request.user, account__provider='github')
    g = Github(gh_access_token_set.first().__str__())
    o = list(g.get_user().get_orgs())

    organisation = request.GET.get('org')
    repo = request.GET.get('repo')
    branches={}
    val=1

    if organisation == g.get_user().login:
        repo_obj = ""
        for i in g.get_user().get_repos():
            if i.name == repo:
                repo_obj = i
                break
        for i in repo_obj.get_branches():
            branches[val]=i.name
            val+=1
    else:
        obj = g.get_user().get_orgs()
        org_obj=""
        repo_obj=""
        for i in obj:
            if i.name == organisation:
                org_obj = i 
                break
        for i in org_obj.get_repos():
            if i.name == repo:
                repo_obj = i 
                break
        for i in repo_obj.get_branches():
            branches[val]=i.name
            val+=1

    return render(request,'response.html',{'dictionary':branches})

@login_required(login_url='/accounts/login')
def getIRISbranches(request):
    repo = request.GET.get('repo')
    gl_access_token_set = SocialToken.objects.filter(account__user=request.user, account__provider='gitlab')
    gl = gitlab.Gitlab(url='https://git.iris.nitk.ac.in', oauth_token=gl_access_token_set.first().__str__())
    gl.auth()
    repo_obj = ""
    for i in gl.projects.list(get_all=True):
        if i.name == repo:
            repo_obj = i 
            break

    branches = repo_obj.branches.list(get_all=True)
    branches_dictionary = {}
    val = 1
    for i in branches:
        branches_dictionary[val] = i.name
        val+=1

    return render(request,'response.html',{'dictionary':branches_dictionary})


@login_required(login_url='/accounts/login/')
def deploy(request):
    org_name = request.POST.get('orgselect')
    repo_name = request.POST.get('repos')
    branch = request.POST.get('branches')
    social  = request.POST.get('social_provider')
    token_obj = SocialToken.objects.filter(account__user= request.user, account__provider=social)
    token = json.loads(serializers.serialize('json', token_obj))[0]['fields']['token']
    org_obj=""
    repo_obj=""
    if social == "github":
        gh_access_token_set = SocialToken.objects.filter(account__user=request.user, account__provider='github')
        g = Github(gh_access_token_set.first().__str__())
        obj = g.get_user().get_orgs()
        if org_name == g.get_user().login:
            for i in g.get_user().get_repos():
                if i.name == repo_name:
                    repo_obj = i
                    break
        else:
            obj = g.get_user().get_orgs()
            org_obj=""
            repo_obj=""
            for i in obj:
                if i.name == organisation:
                    org_obj = i 
                    break
            for i in org_obj.get_repos():
                if i.name == repo_name:
                    repo_obj = i 
                    break
        url = repo_obj.clone_url
    else:
        url = "https://git.iris.nitk.ac.in/IRIS-NITK/"+repo_name+".git"
    deploy_from_git.delay(token,url,social,org_name,repo_name,branch)
    return HttpResponse("hi")
