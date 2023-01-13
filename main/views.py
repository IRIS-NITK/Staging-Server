from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from allauth.socialaccount.models import SocialToken
from github import Github
import gitlab,json,time,os,subprocess
from django.http import HttpResponse,StreamingHttpResponse
from django.shortcuts import render,redirect
from main.tasks.services import deploy_from_git, stop_container, deploy_from_git_template, get_repo_info, clean_up
from main.tasks import findfreeport
from django.core import serializers
from django.core.exceptions import ObjectDoesNotExist
from main.models import RunningInstance
from django.template import Context, loader
from .forms import DeployTemplateForm
from .models import DeployTemplate
import requests

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
    container_name = f"iris_{instance.organisation}_{instance.repo_name}_{instance.branch}"
    clean_up(
        org_name = instance.organisation,
        repo_name = instance.repo_name,
        remove_container = container_name
    )
    instance.status = RunningInstance.STATUS_STOPPED
    return redirect('deploy_template_dashboard')

@login_required
def deploy_instance_delete(request, pk):
    instance = RunningInstance.objects.get(pk=pk)
    instance.delete()
    return redirect('form',social=instance.social)

@login_required
def deploy_instance_redeploy(request, pk):
    # TODO : doesn't work yet 
    instance = RunningInstance.objects.get(pk=pk)
    try:
        template = DeployTemplate.objects.get(
        social_type = instance.social,
        organisation_or_user = instance.organisation,
        default_branch = instance.branch,
        )
    except ObjectDoesNotExist:
        return HttpResponse("Template not found, was this deployed from a template ?")
    return redirect('deploy_from_template', pk=template.pk)


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
    docker_env_variables = json.loads(template.docker_env_vars)
    docker_volumes = json.loads(template.docker_volumes)
    internal_port = template.internal_port
    dockerfile_path = template.dockerfile_path
    docker_network = template.docker_network
    
    user_name, repo_name = get_repo_info(repo_url)

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
            instance.exposed_port = external_port
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

@login_required
def deploy_template_clean_up(request, pk):
    # def clean_up(org_name, repo_name, remove_container = False, remove_volume = False, remove_network = False, remove_image = False, remove_branch_dir = False, remove_all_dir = False, remove_user_dir = False):
    instance = RunningInstance.objects.get(pk=pk)
    if request.method == 'POST':
        repo_name = instance.repo_name
        org_name = instance.organisation
        container_name = f"iris_{org_name}_{repo_name}_{instance.branch}"
        print(f"Cleaning up {container_name}")
        res, logs = clean_up(
            org_name = org_name,
            repo_name = repo_name,
            remove_container = container_name,
            remove_branch_dir=instance.branch,
        )
        if res:
            instance.status = RunningInstance.STATUS_STOPPED
            instance.save()

    return redirect('form',social=instance.social)

 
@login_required
def deploy_template_duplicate(request, pk):
    template = DeployTemplate.objects.get(pk=pk)
    if request.method == 'POST':
        duplicate_template = DeployTemplate.objects.create(
            name = template.name + " (copy)",
            social_type = template.social_type,
            organisation_or_user = template.organisation_or_user,
            git_repo_url = template.git_repo_url,
            access_token = template.access_token,
            default_branch = template.default_branch,
            docker_image = template.docker_image,
            docker_network = template.docker_network,
            docker_volumes = template.docker_volumes,
            docker_env_vars = template.docker_env_vars,
            internal_port = template.internal_port,
            dockerfile_path = template.dockerfile_path
        )
        duplicate_template.save()
    return redirect('deploy_template_list')
        

@login_required(login_url='/accounts/login/')
def home(response):

    # PyGithub: https://pygithub.readthedocs.io/en/latest/introduction.html
    gh_access_token_set = SocialToken.objects.filter(account__user=response.user, account__provider='github')
    if (len(gh_access_token_set) == 0):
        print("No Github Access Token")
    else:
        github_client = Github(gh_access_token_set.first().__str__())
        print(github_client.get_user().login)

    gl_access_token_set = SocialToken.objects.filter(account__user=response.user, account__provider='gitlab')
    if (len(gl_access_token_set) == 0):
        print("No Gitlab Access Token")
    else:
        # Python Gitlab: https://python-gitlab.readthedocs.io/en/stable/
        gitlab_client = gitlab.Gitlab(url='https://git.iris.nitk.ac.in', oauth_token=gl_access_token_set.first().__str__())
        try:
            gitlab_client.auth()
        except:
            return redirect("account_logout")
        print(gitlab_client.user.emails.list())

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
        repos = { i + 1 : project.name for i,project in enumerate(projects) }
        # repos = {}
        # val = 1
        # for i in projects:
        #     repos[val] = i.name
        #     val+=1
        instances = RunningInstance.objects.filter(organisation="IRIS-NITK")
        return render(request,'gitlab_form.html',{'instances':instances,'repos':repos})
    
@login_required(login_url='/accounts/login/')
def getrepos(request):

    gh_access_token_set = SocialToken.objects.filter(account__user=request.user, account__provider='github')
    github_client = Github(gh_access_token_set.first().__str__())

    organization_name = request.GET.get('org')
    repositories = {}

    if organization_name == github_client.get_user().login:
        for repo in github_client.get_user().get_repos():
            repositories[repo.name] = repo.name
    else:
        organizations = list(github_client.get_user().get_orgs())
        for org in organizations:
            if org.name == organization_name:
                for repo in org.get_repos():
                    repositories[repo.name] = repo.name
                break

    return render(request, 'response.html', {'dictionary': repositories})

@login_required(login_url='/accounts/login/')
def getbranches(request):

    gh_access_token_set = SocialToken.objects.filter(account__user=request.user, account__provider='github')
    github_client = Github(gh_access_token_set.first().__str__())
    organizations = list(github_client.get_user().get_orgs())

    organization_name = request.GET.get('org')
    repo_name = request.GET.get('repo')
    branches = {}

    if organization_name == github_client.get_user().login:
        for repo in github_client.get_user().get_repos():
            if repo.name == repo_name:
                for branch in repo.get_branches():
                    branches[branch.name] = branch.name
                break
    else:
        for org in organizations:
            if org.name == organization_name:
                for repo in org.get_repos():
                    if repo.name == repo_name:
                        for branch in repo.get_branches():
                            branches[branch.name] = branch.name
                        break
                break

    return render(request,'response.html',{'dictionary': branches})

@login_required(login_url='/accounts/login')
def getIRISbranches(request):

    repo_name = request.GET.get('repo')
    gl_access_token_set = SocialToken.objects.filter(account__user=request.user, account__provider='gitlab')
    gitlab_client = gitlab.Gitlab(url='https://git.iris.nitk.ac.in', oauth_token=gl_access_token_set.first().__str__())
    gitlab_client.auth()

    repo_object = None
    for project in gitlab_client.projects.list(get_all=True):
        if project.name == repo_name:
            repo_object = project 
            break

    branches_dictionary = {}
    if repo_object:
        for branch in repo_object.branches.list(get_all=True):
            branches_dictionary[branch.name] = branch.name

    return render(request,'response.html',{'dictionary': branches_dictionary})

@login_required(login_url='/accounts/login/')
def deploy_wrapper(request):
    return redirect('deploy',org_name = request.POST.get('orgselect'),repo_name = request.POST.get('repos'),branch = request.POST.get('branches'),social  = request.POST.get('social_provider'))


@login_required(login_url='/accounts/login/')
def deploy(request,org_name,repo_name,branch,social):

    token_obj = SocialToken.objects.filter(account__user=request.user, account__provider=social)
    token = json.loads(serializers.serialize('json', token_obj))[0]['fields']['token']
    external_port = findfreeport.find_free_port()
    url = ""
    if social == "github":
        gh_access_token_set = SocialToken.objects.filter(account__user=request.user, account__provider='github')
        github_client = Github(gh_access_token_set.first().__str__())
        if org_name == github_client.get_user().login:
            repos = github_client.get_user().get_repos()
        else:
            repos = github_client.get_organization(org_name).get_repos()
        for repo in repos:
            if repo.name == repo_name:
                url = repo.clone_url
                break
    else:
        url = "ssh://git@git.iris.nitk.ac.in:5022/IRIS-NITK/IRIS.git"
        token = None 
        # url = "https://git.iris.nitk.ac.in/IRIS-NITK/" + repo_name + ".git"

    try:
        instance = RunningInstance.objects.get(social=social,organisation=org_name,repo_name=repo_name,branch= branch)
        instance.owner = request.user.username
        instance.update_time = time.time()
        instance.external_port = external_port
        instance.save()
    except ObjectDoesNotExist:
        instance = RunningInstance(
           branch=branch, owner=request.user.username, status=RunningInstance.STATUS_PENDING,repo_name =repo_name,organisation=org_name,social=social,exposed_port=external_port
        )
        instance.save()


    deploy_from_git.delay(
        external_port = external_port,
        token = token, 
        url = url,
        social = social,
        org_name = org_name,
        repo_name = repo_name,
        branch_name = branch
    )
    return redirect('form', social=social)


@login_required(login_url='/accounts/login/')
def logs(request,social,branch,reponame,orgname):
    path_to_home_dir = os.getenv("PATH_TO_HOME_DIR")
    try:
        log_file_name = f"{path_to_home_dir}/{orgname}/{reponame}/{branch}/{branch}.txt"
        with open(log_file_name, "r") as f:
            data = f.read()
        context = {'data': data, 'social': social, 'branch': branch, 'reponame': reponame, 'orgname': orgname}
        return render(request, 'log.html', context)
    except:
        return render(request, 'failure.html')

@login_required(login_url='/accounts/login/')
def stop(request,social,orgname,reponame,branch):
    def generate_stream():
        yield response_header.render({"purpose": "stopping"})
        yield "<pre><code >"
        try:
            instance = RunningInstance.objects.get(branch=branch, repo_name=reponame, organisation=orgname)
            yield from stop_container(branch, reponame, orgname)
            yield "</code></pre>"
            instance.delete()
            yield response_footer.render(
                {"status_message": "The server was stopped successfully", 'social': social}
            )
        except ObjectDoesNotExist:
            yield "</code></pre>"
            yield response_footer.render(
                {"status_message": "The server failed to stop properly", 'social': social}
            )

    response = StreamingHttpResponse(generate_stream())
    del response["Content-Length"]
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response

@login_required(login_url='/accounts/login/')
def get_container_logs(request, social, orgname, reponame, branch):
    prefix = "iris"
    container_name = f"{prefix}_{orgname}_{reponame}_{branch}"
    command = ["docker", "logs", "-f", container_name]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def generate_stream():
        yield response_header.render({"purpose": "Starting"})
        yield "<pre><code >"
        while process.poll() is None:
            output = process.stdout.readline()
            logs = output.decode("utf-8")
            yield logs
        output, errors = process.communicate()
        if errors:
            logs = errors.decode("utf-8")
            yield logs


    response = StreamingHttpResponse(generate_stream())
    del response["Content-Length"]
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


@login_required
def check_uptime_status(request, pk):
    instance = RunningInstance.objects.get(pk = pk)
    url = f"http://localhost:{instance.exposed_port}"
    try:
        res = (requests.get(url, timeout=5).status_code == 200)
    except:
        res = False 
    if instance.status !=(RunningInstance.STATUS_SUCCESS) and res:
        instance.status = RunningInstance.STATUS_SUCCESS
    if instance.status == RunningInstance.STATUS_SUCCESS and not res:
        instance.status = RunningInstance.STATUS_STOPPED
    instance.save()
    return redirect('form', social=instance.social)
    