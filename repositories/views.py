import json, os, time

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseRedirect

from repositories.models import Repository
from repositories.utils.helpers import extractRepositoryName, generate_deployment_id
from repositories.services import create as create_repository, get_branches, deploy as deploy_branch

from main.services import delete_instance, clean_up
from main.models import RunningInstance
from main.utils.helpers import get_app_container_name, get_db_container_name
DEPLOYMENT_DOCKER_NETWORK = os.getenv("DEPLOYMENT_DOCKER_NETWORK", "IRIS") # Docker network for iris containers
PREFIX = os.getenv("PREFIX", "iris")  # Prefix for docker container names
SUBDOMAIN_PREFIX = os.getenv("SUBDOMAIN_PREFIX", "staging")  # Prefix for domain name
DOMAIN = os.getenv("DOMAIN", "iris.nitk.ac.in")  # Domain name
PATH_TO_HOME_DIR = os.getenv("PATH_TO_HOME_DIR")  # Path to home directory

def index(request):
    repositories = Repository.objects.all()
    return render(request, 'repositories/index.html', {'repositories': repositories})

@login_required
@require_POST
def create(request):

    repo_git_url = request.POST.get('repo_git_url', None)
    access_token = request.POST.get('access_token', None)
    repo_username = request.POST.get('username', None)
    db_image = request.POST.get('db_image', None)
    dockerfile = request.POST.get('dockerfile', None)
    internal_port = int(request.POST.get('internal_port', None))


    app_env_keys = request.POST.getlist("app_env_key[]")
    app_env_values = request.POST.getlist("app_env_value[]")
    app_env_list = json.dumps(list(zip(app_env_keys, app_env_values)))

    db_env_keys = request.POST.getlist("db_env_key[]")
    db_env_values = request.POST.getlist("db_env_value[]")
    db_env_list = json.dumps(list(zip(db_env_keys, db_env_values)))
    deployer = User.objects.get(id=request.user.id)
    try: 
        repo_name = extractRepositoryName(repo_git_url)
        repository = Repository(
            deployer=deployer,
            repo_git_url=repo_git_url,
            repo_name=repo_name,
            access_token=access_token,
            repo_username=repo_username,
            db_image=db_image,
            dockerfile_path=dockerfile,
            internal_port=internal_port,
            app_env_vars=app_env_list,
            db_env_vars=db_env_list
        )
        repository.save()
    except Exception as e:
        print(e)
        return redirect('repositories_dashboard')
    create_repository.delay(repo_git_url=repo_git_url,
           access_token=access_token,
           repo_username=repo_username,
           repo_name=repo_name,
           deployer=request.user.username,
           repository_pk=repository.pk)
    return redirect('repositories_dashboard')

@login_required
@require_POST
def update_repository(request, pk):
    update_access_token = request.POST.get('update_access_token', None)
    try:
        repository = Repository.objects.get(pk=pk)
        if update_access_token:
            repository.access_token = request.POST.get('access_token', None)
        repository.repo_username = request.POST.get('username', None)
        repository.db_image = request.POST.get('db_image', None)
        repository.dockerfile_path = request.POST.get('dockerfile', None)
        repository.internal_port = int(request.POST.get('internal_port', None))

        app_env_keys = request.POST.getlist("app_env_key[]")
        app_env_values = request.POST.getlist("app_env_value[]")

        repository.app_env_vars = json.dumps(list(zip(app_env_keys, app_env_values)))

        db_env_keys = request.POST.getlist("db_env_key[]")
        db_env_values = request.POST.getlist("db_env_value[]")
        repository.app_env_db_host_key = request.POST.get("app_env_db_host_key")
        repository.db_env_vars = json.dumps(list(zip(db_env_keys, db_env_values)))

        repository.save()
    except Exception as e:
        print(e)
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    
@login_required
def repository_dashboard(request, pk):
    repository = Repository.objects.get(pk=pk)
    repository_instances = RunningInstance.objects.filter(repository=repository)

    status, branches = get_branches(repository.deployer.username, repository.pk, repository.repo_name)
    if not status:
        branches = ["DEFAULT_BRANCH"]
    app_env_vars = json.loads(repository.app_env_vars)
    db_env_vars = json.loads(repository.db_env_vars)
    return render(request,
                  'repositories/repository_dashboard.html',
                  {'repository': repository,
                    'repository_instances': repository_instances,
                    'branches': branches,
                    'app_env_vars': app_env_vars,
                    'db_env_vars': db_env_vars})


@login_required
@require_POST
def deploy(request, pk, branch=None):
    branch = request.POST.get('branch', None)
    if not branch:
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    branch = request.POST.get('branch', branch)

    try:
        repository = Repository.objects.get(pk=pk)
    except ObjectDoesNotExist:
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    deployment_id = generate_deployment_id(repository_pk=repository.pk,
                                               repo_name=repository.repo_name,
                                               branch=branch,
                                               domain=DOMAIN,
                                               subdomain_prefix=SUBDOMAIN_PREFIX)
    try:
        instance = RunningInstance.objects.get(
            deployment_id=deployment_id
        )
        instance.owner = request.user.username
        instance.update_time = time.time()
        app_env_vars = repository.app_env_vars if repository.app_env_vars else {}
        app_env_vars.update({
                    repository.app_env_db_host_key: instance.db_container_name
                    })
        instance.app_env_vars = app_env_vars
        instance.db_env_vars = repository.db_env_vars
        instance.dockerfile_path = repository.dockerfile_path
        instance.internal_port = int(repository.internal_port)
        instance.repository = repository
        instance.log_file_path = f"{PATH_TO_HOME_DIR}/logs/repositories/{repository.deployer.username}/{repository.pk}/{branch}/{branch}.txt"
        instance.branch_deploy_path = f"{PATH_TO_HOME_DIR}/repositories/{repository.deployer.username}/{repository.pk}/{branch}"
        instance.save()
    except ObjectDoesNotExist:
        app_container_name = get_app_container_name(PREFIX, deployment_id)
        db_container_name = get_db_container_name(PREFIX, deployment_id)
        app_env_vars = dict(json.loads(repository.app_env_vars)) if repository.app_env_vars else {}
        db_env_vars = dict(json.loads(repository.db_env_vars)) if repository.db_env_vars else {}
        app_env_vars.update({
                    repository.app_env_db_host_key: db_container_name
                    })
        instance = RunningInstance(
            social="repositories",
            repo_name=repository.repo_name,
            organisation=repository.deployer.username,
            branch=branch,
            owner=request.user.username,
            update_time=time.time(),
            internal_port=int(repository.internal_port),
            app_container_name = app_container_name,
            db_container_name = db_container_name,
            dockerfile_path = repository.dockerfile_path,
            deployment_id = deployment_id,
            deployed_url = f"https://staging-{deployment_id}.iris.nitk.ac.in",
            app_docker_image = None,
            db_docker_image = repository.db_image,
            app_env_vars = app_env_vars,
            db_env_vars = db_env_vars,
            repository = repository,
            log_file_path = f"{PATH_TO_HOME_DIR}/logs/repositories/{repository.deployer.username}/{repository.pk}/{branch}/{branch}.txt",
            branch_deploy_path = f"{PATH_TO_HOME_DIR}/repositories/{repository.deployer.username}/{repository.pk}/{branch}"
        )
        instance.save()
        repository.deployments += 1
        repository.save()
    except Exception as e:
        print(e)
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    deploy_branch(branch=branch,
                        repository=repository,
                        instance=instance)
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

@login_required
def stop_instance(request, pk):
    stop_db= request.POST.get('stop_db', False)
    try:
        instance = RunningInstance.objects.get(pk=pk)
        if instance.repository:
            repository = Repository.objects.get(pk=instance.repository.pk)
            repository.deployments -= 1
            repository.save()
        print("DELETING_INSTANCE")
        delete_instance(instance, stop_db=stop_db)
    except ObjectDoesNotExist:
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

@login_required
def delete_repository(request, pk):
    try:
        repository = Repository.objects.get(pk=pk)
        Instances = RunningInstance.objects.filter(repository=repository)
        for instance in Instances:
            delete_instance(instance, stop_db=True, remove_branch_dir=False)
        clean_up_dir = f"{PATH_TO_HOME_DIR}/repositories/{repository.deployer.username}/{repository.pk}"
        log_file_path = f"{PATH_TO_HOME_DIR}/logs/repositories/{repository.deployer.username}/{repository.pk}/DEFAULT_BRANCH/DEFAULT_BRANCH.txt"
        clean_up(
        org_name="repositories",
        repo_name=repository.repo_name,
        branch=None,
        deployment_id=None,
        branch_name=None,
        remove_container=None,
        remove_branch_dir=None,
        remove_nginx_conf=True,
        log_file_path=log_file_path,
        branch_deploy_path=None,
        remove_repo=True,
        repo_path=clean_up_dir
        )
        repository.delete()
    except ObjectDoesNotExist:
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    return redirect('repositories_dashboard')
