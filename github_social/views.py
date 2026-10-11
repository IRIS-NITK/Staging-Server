import time
import logging

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render

from django.conf import settings
from main.models import RunningInstance
from main.services import delete_instance, stop_instance
from main.utils.helpers import generate_deployment_id, get_app_container_name, get_db_container_name, get_deployed_url
from github_social.services import deploy as deploy_github_social
from github_social.services import get_github_token

logger = logging.getLogger(__name__)


@login_required
def index(request):
    status, _, github_client = get_github_token(request)
    if not status:
        return redirect('account_logout')

    user = github_client.get_user()
    user_repos = []
    owners = [user.login]
    for org in user.get_orgs():
        owners.append(org.login)

    for repo in user.get_repos():
        user_repos.append({
            'name': repo.name,
            'full_name': repo.full_name,
            'owner': repo.owner.login,
        })

    for org in user.get_orgs():
        try:
            for repo in org.get_repos():
                user_repos.append({
                    'name': repo.name,
                    'full_name': repo.full_name,
                    'owner': repo.owner.login,
                })
        except Exception:
            continue

    try:
        instances = RunningInstance.objects.filter(social='github').exclude(repo_name='IRIS')
    except Exception:  # pragma: no cover - defensive fallback
        instances = None

    return render(request, 'github_social/index.html', {
        'owners': owners,
        'repositories': user_repos,
        'instances': instances,
        'github_url': 'https://github.com',
    })


@login_required
def get_projects(request):
    owner = request.GET.get('owner')
    if not owner:
        return JsonResponse({'error': 'Invalid owner'})

    status, _, github_client = get_github_token(request)
    if not status:
        return redirect('account_logout')

    try:
        if owner == github_client.get_user().login:
            repos = github_client.get_user().get_repos()
        else:
            repos = github_client.get_organization(owner).get_repos()
    except Exception:
        return JsonResponse({'error': 'Unable to list repositories'})

    project_options = '<option selected disabled>Choose...</option>'
    for repo in repos:
        project_options += f'<option value="{repo.name}">{repo.name}</option>'
    return JsonResponse({'project_options': project_options})


@login_required
def get_branches(request):
    owner = request.GET.get('owner')
    project = request.GET.get('project')
    if not owner or not project:
        return JsonResponse({'error': 'Invalid repository selection'})

    status, _, github_client = get_github_token(request)
    if not status:
        return redirect('account_logout')

    try:
        repo = github_client.get_repo(f'{owner}/{project}')
        branches = repo.get_branches()
    except Exception:
        return JsonResponse({'error': 'Unable to list branches'})

    branch_options = '<option selected disabled>Choose...</option>'
    for branch in branches:
        branch_options += f'<option value="{branch.name}">{branch.name}</option>'
    return JsonResponse({'branch_options': branch_options})


@login_required
def deploy(request, pk=0):
    status, access_token, github_client = get_github_token(request)
    if not status:
        return redirect('account_logout')

    project = request.POST.get('project')
    owner = request.POST.get('owner')
    branch = request.POST.get('branch')
    internal_port = request.POST.get('internal_port')
    docker_image = request.POST.get('docker_image')
    dockerfile = request.POST.get('dockerfile')

    project_name = ""
    project_url = ""
    deployment_id = None

    if pk != 0:
        try:
            instance = RunningInstance.objects.get(pk=pk)
            project_name = instance.repo_name
            branch = instance.branch
            docker_image = instance.app_docker_image
            dockerfile = instance.app_dockerfile
            internal_port = instance.internal_port
            deployment_id = instance.deployment_id
            project_url = instance.project_url
        except Exception:
            return redirect('github_social_dashboard')
    else:
        project_name = project
        project_url = f'https://github.com/{owner}/{project}.git'
        owner = owner or github_client.get_user().login

    group_name = owner or github_client.get_user().login

    try:
        instance = RunningInstance.objects.get(
            social='github',
            organisation=group_name,
            repo_name=project_name,
            branch=branch,
        )
        instance.owner = request.user.username
        instance.update_time = time.time()
        instance.internal_port = internal_port
        instance.status = RunningInstance.STATUS_PENDING
        instance.app_docker_image = docker_image
        instance.app_dockerfile = dockerfile
        deployment_id = instance.deployment_id
        instance.deployed_url = get_deployed_url(deployment_id)
        instance.save()
    except ObjectDoesNotExist:
        deployment_id = generate_deployment_id(
            group_name,
            project_name,
            branch,
            settings.STAGING_CONF['DOMAIN'],
            settings.STAGING_CONF['SUBDOMAIN_PREFIX'],
        )
        app_container_name = get_app_container_name(settings.STAGING_CONF['PREFIX'], deployment_id)
        db_container_name = get_db_container_name(settings.STAGING_CONF['PREFIX'], deployment_id)
        instance = RunningInstance(
            social='github',
            organisation=group_name,
            repo_name=project_name,
            branch=branch,
            internal_port=internal_port,
            owner=request.user.username,
            update_time=time.time(),
            status=RunningInstance.STATUS_PENDING,
            deployed_url=get_deployed_url(deployment_id),
            project_url=project_url,
            app_container_name=app_container_name,
            db_container_name=db_container_name,
            deployment_id=deployment_id,
            app_docker_image=docker_image,
            app_dockerfile=dockerfile,
        )
        instance.save()

    if docker_image == '' or len(docker_image) == 0:
        docker_image = None

    try:
        task = deploy_github_social(
            url=project_url,
            user_name='x-access-token',
            group=group_name,
            project=project_name,
            branch=branch,
            internal_port=internal_port,
            deployment_id=deployment_id,
            docker_image=docker_image,
            token=access_token,
            dockerfile=dockerfile,
        )
        logger.info(
            "Queued deployment %s for instance %s",
            task.id,
            instance.pk,
        )
    except Exception:
        logger.exception("Unable to queue deployment for instance %s", instance.pk)
        instance.status = RunningInstance.STATUS_ERROR
        instance.save(update_fields=["status", "update_time"])

    return redirect('github_social_dashboard')


@login_required
def stop(request, pk, stop_db=False):
    try:
        instance = RunningInstance.objects.get(pk=pk)
    except Exception:
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    stop_instance(instance, stop_db)
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


@login_required
def stop_with_db(request, pk):
    return stop(request, pk, stop_db=True)


@login_required
def delete(request, pk):
    try:
        instance = RunningInstance.objects.get(pk=pk)
    except Exception:
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    delete_instance(instance, stop_db=True)
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


@login_required
def health_check(request, pk):
    try:
        instance = RunningInstance.objects.get(pk=pk)
    except Exception:
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
