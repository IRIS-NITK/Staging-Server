from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from allauth.socialaccount.models import SocialToken
from github import Github
import gitlab,json,time,os,subprocess
from django.http import HttpResponse,StreamingHttpResponse
from django.shortcuts import render,redirect
from main.tasks.services import deploy_from_git, stop_container, deploy_from_git_template, get_repo_name, clean_up
from main.tasks import findfreeport
from django.core import serializers
from django.core.exceptions import ObjectDoesNotExist
from main.models import RunningInstance
from django.template import Context, loader
from .forms import DeployTemplateForm
from .models import DeployTemplate

response_header = loader.get_template("response_header.html")
response_footer = loader.get_template("response_footer.html")
log_template = loader.get_template("log.html")


def deploy_template_dashboard(request):
    return render(request, 'template_dashboard.html', context={
        "instances": RunningInstance.objects.all() 
    })

@login_required
def deploy_template_list(request):
    templates = DeployTemplate.objects.filter()
    return render(request, 'template_list.html', {'templates': templates})

@login_required
def deploy_template_form(request):
    if request.method == 'POST':
        form = DeployTemplateForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('/')
    else:
        form = DeployTemplateForm()
    return render(request, 'template_form.html', {'form': form})

@login_required
def deploy_template_update(request, pk):
    template = DeployTemplate.objects.get(pk=pk)
    if request.method == 'POST':
        form = DeployTemplateForm(request.POST, instance=template)
        if form.is_valid():
            form.save()
            return redirect('deploy_template_list')
    else:
        form = DeployTemplateForm(instance=template)
    return render(request, 'template_form.html', {'form': form})

@login_required
def deploy_template_delete(request, pk):
    template = DeployTemplate.objects.get(pk=pk)
    template.delete()
    return redirect('deploy_template_list')

@login_required
def deploy_template_stop(request, pk):
    instance = RunningInstance.objects.get(pk=pk)
    prefix = "iris_template"
    container_name = f"{prefix}_{instance.organisation}_{instance.repo_name}_{instance.branch}"
    clean_up(
        org_name = instance.organisation,
        repo_name = instance.repo_name,
        remove_container = container_name
    )
    instance.status = RunningInstance.STATUS_STOPPED
    return redirect('deploy_template_dashboard')

@login_required
def deploy_from_template(request, pk):
    template = DeployTemplate.objects.get(pk=pk)

    social = template.social_type
    # access_token = SocialToken.objects.get(account__user=request.user, account__provider=social).token
    access_token = template.access_token
    org_name = template.organisation_or_user
    repo_url = template.git_repo_url
    default_branch = template.default_branch
    docker_image = template.docker_image
    docker_env_variables = template.docker_env_vars
    docker_volumes = template.docker_volumes
    internal_port = template.internal_port
    dockerfile_path = template.dockerfile_path
    docker_network = template.docker_network
    
    repo_name = get_repo_name(repo_url)

    if request.method == 'POST':
        external_port = findfreeport.find_free_port()
        try:
            instance = RunningInstance.objects.get(
                social=social,
                organisation=org_name,
                repo_name=repo_name,
                branch=default_branch
            )
            instance.owner = request.user.username
            instance.update_time = time.time()
            instance.status = RunningInstance.STATUS_PENDING
            instance.save()
        except ObjectDoesNotExist:
            instance = RunningInstance(
                exposed_port = external_port,
                social=social,
                organisation=org_name,
                repo_name=repo_name,
                branch=default_branch,
                owner=request.user.username,
                update_time=time.time(),
                status=RunningInstance.STATUS_PENDING
            )
            instance.save()

        
        deploy_from_git_template.delay(
            token=access_token,
            social=social,
            org_name=org_name,
            repo_name=repo_name,
            url=repo_url,
            branch_name=default_branch,
            internal_port=internal_port,
            external_port=external_port,
            docker_image=docker_image,
            dockerfile_path=dockerfile_path,
            docker_volumes=docker_volumes,
            docker_env_variables=docker_env_variables,
            default_branch=default_branch,
            docker_network=docker_network
        )

    return redirect('deploy_template_dashboard')

@login_required(login_url='/accounts/login/')
def home(response):
    # Example of how to get the access token for a particular provider
    # PyGithub: https://pygithub.readthedocs.io/en/latest/introduction.html
    # gh_access_token_set = SocialToken.objects.filter(account__user=response.user, account__provider='github')
    # if (len(gh_access_token_set) == 0):
    #     print("No Github Access Token")
    # else:
    #     g = Github(gh_access_token_set.first().__str__())
    #     print("1", g.get_user().login)
    #     for repo in g.get_user().get_orgs():
    #             print(repo.name)

    gl_access_token_set = SocialToken.objects.filter(account__user=response.user, account__provider='gitlab')
    if (len(gl_access_token_set) == 0):
        print("No Gitlab Access Token")
    else:
        # Python Gitlab: https://python-gitlab.readthedocs.io/en/stable/
        gl = gitlab.Gitlab(url='https://git.iris.nitk.ac.in', oauth_token=gl_access_token_set.first().__str__())
        try:
            gl.auth()
        except:
            return redirect("account_logout")
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
    social = social.capitalize()
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
        instances = RunningInstance.objects.filter(social='github')
        return render(request,'form.html',{'instances':instances,'orgs_name':orgs_name})
    else:
        gl_access_token_set = SocialToken.objects.filter(account__user=request.user, account__provider='gitlab')
        gl = gitlab.Gitlab(url='https://git.iris.nitk.ac.in', oauth_token=gl_access_token_set.first().__str__())
        try:
            gl.auth()
        except:
            return redirect("account_login")
        projects = gl.projects.list(get_all=True)
        repos = {}
        val = 1
        for i in projects:
            repos[val] = i.name
            val+=1
        instances = RunningInstance.objects.all()
        return render(request,'gitlabform.html',{'instances':instances,'repos':repos})
    
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
    try:
        gl.auth()
    except:
        return redirect("account_login")
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
def deploy_wrapper(request):
    return redirect('deploy',org_name = request.POST.get('orgselect'),repo_name = request.POST.get('repos'),branch = request.POST.get('branches'),social  = request.POST.get('social_provider'))


@login_required(login_url='/accounts/login/')
def deploy(request,org_name,repo_name,branch,social):
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
                if i.name == org_name:
                    org_obj = i 
                    break
            for i in org_obj.get_repos():
                if i.name == repo_name:
                    repo_obj = i 
                    break
        url = repo_obj.clone_url
    else:
        url = "https://git.iris.nitk.ac.in/IRIS-NITK/"+repo_name+".git"
    
    try:
        instance = RunningInstance.objects.get(social=social,organisation=org_name,repo_name=repo_name,branch= branch)
        instance.owner = request.user.username
        instance.update_time = time.time()
        instance.save()
    except ObjectDoesNotExist:
        instance = RunningInstance(
           branch=branch, owner=request.user.username, status=RunningInstance.STATUS_PENDING,repo_name =repo_name,organisation=org_name,social=social
        )
        instance.save()
    deploy_from_git.delay(token,url,social,org_name,repo_name,branch)
    instances = RunningInstance.objects.filter(social=social,organisation=org_name)
    # return render(request,'display.html',{'instances':instances})
    return redirect('form',social=social)


@login_required(login_url='/accounts/login/')
def logs(request,social,branch,reponame,orgname):
    PATH_TO_HOME_DIR = os.getenv("PATH_TO_HOME_DIR")
    DEFAULT_BRANCH = "main"
    try:
        log_file_name = f'{PATH_TO_HOME_DIR}/{orgname}/{reponame}/{DEFAULT_BRANCH}/{branch}'+".txt"
        f = open(log_file_name,"r")
        data = f.read()
        context ={'data': data,'social':social}
        return render(request,'log.html',context)
    except :
        return render(request,'failure.html',)

@login_required(login_url='/accounts/login/')
def stop(request,social,orgname,reponame,branch):
    def generate_stream():
        yield response_header.render({"purpose": "stopping"})
        yield "<pre><code >"
        try:
            instance = RunningInstance.objects.get(branch=branch,repo_name=reponame,organisation=orgname)
            yield from stop_container(branch,reponame,orgname)
            yield "</code></pre>"
            instance.delete()
            yield response_footer.render(
                    {"status_message": "The server was stopped successfully",
                    'social':social
                    }
                )
        except ObjectDoesNotExist:
            yield "</code></pre>"
            yield response_footer.render(
                    {"status_message": "The server failed to stop properly",
                    'social':social
                    }
                )
    response = StreamingHttpResponse(generate_stream())
    del response["Content-Length"]
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response

@login_required(login_url='/accounts/login/')
def getcontainerlogs(request,social,orgname,reponame,branch):
    prefix = "iris"
    container_name = f"{prefix}_{orgname}_{reponame}_{branch}" 
    command = ["docker", "logs", "-f", container_name]
    process = subprocess.Popen(command, stdout=subprocess.PIPE)
    logs = ""
    while True:
        output = process.stdout.readline()
        if output == b'':
            break
        logs += output.decode('utf-8')
    # template = Template("{{ logs }}")
    context = {"data": logs,"social":social}
    return HttpResponse(log_template.render(context))