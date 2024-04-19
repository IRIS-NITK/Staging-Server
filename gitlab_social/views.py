import os
import time
import gitlab
from dotenv import load_dotenv
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, HttpResponse
from django.core.exceptions import ObjectDoesNotExist
from django import forms
from django.http import JsonResponse, HttpResponseRedirect
from allauth.socialaccount.models import SocialToken
from main.models import RunningInstance
from main.services import delete_instance
from gitlab_social.services import deploy as deploy_gitlab_social
from gitlab_social.services import get_gitlab_token

from main.utils.helpers import get_app_container_name, get_db_container_name, generate_deployment_id


from django.conf import settings


@login_required
def index(request):

    # Check if the user is authenticated
    if not request.user.is_authenticated:
        return redirect("account_login")

    # Get GitLab access token for the current user
    status, _, gitlab_client = get_gitlab_token(request)
    if not status:
        return redirect("account_logout")

    groups = gitlab_client.groups.list()

    try:
        instances = RunningInstance.objects\
            .filter(social='git.iris')\
            .exclude(repo_name='IRIS')
    except:  # pylint: disable=bare-except
        instances = None

    return render(request, 'gitlab_social/index.html', context={'groups': groups, 'instances': instances, 'gitlab_url': settings.SOCIALACCOUNT_PROVIDERS['gitlab']['GITLAB_URL']})


@login_required
def get_projects(request):
    group_id = request.GET.get('group_id', None)
    if group_id:
        gl_access_token_set = SocialToken.objects.filter(
            account__user=request.user, account__provider='gitlab')
        gl = gitlab.Gitlab(
            url=settings.SOCIALACCOUNT_PROVIDERS['gitlab']['GITLAB_URL'],
            oauth_token=gl_access_token_set.first().__str__()
        )

        try:
            # Authenticate the GitLab client
            gl.auth()
        except:  # pylint: disable=bare-except
            return redirect("account_logout")

       # gl = gitlab.Gitlab(settings.SOCIALACCOUNT_PROVIDERS['gitlab']['GITLAB_URL'], private_token=settings.STAGING_CONF['ACCESS_TOKEN'])
        group = gl.groups.get(group_id)
        projects = gl.projects.list(get_all=True)
        project_options = '<option selected disabled>Choose...</option>'
        for project in projects:
            project_options += f'<option value="{project.id}">{project.name}</option>'
        data = {'project_options': project_options}
        return JsonResponse(data)
    else:
        return JsonResponse({'error': 'Invalid group ID'})


@login_required
def get_branches(request):
    project_id = request.GET.get('project_id', None)
    if project_id:
        gl_access_token_set = SocialToken.objects.filter(
            account__user=request.user, account__provider='gitlab')
        gl = gitlab.Gitlab(
            url=settings.SOCIALACCOUNT_PROVIDERS['gitlab']['GITLAB_URL'],
            oauth_token=gl_access_token_set.first().__str__()
        )

        try:
            # Authenticate the GitLab client
            gl.auth()
        except:  # pylint: disable=bare-except
            return redirect("account_logout")
        # gl = gitlab.Gitlab(GITLAB_SERVER, private_token=settings.STAGING_CONF['ACCESS_TOKEN'])
        project = gl.projects.get(project_id)
        branches = project.branches.list()
        branch_options = '<option selected disabled>Choose...</option>'
        for branch in branches:
            branch_options += f'<option value="{branch.name}">{branch.name}</option>'
        data = {'branch_options': branch_options}
        return JsonResponse(data)
    else:
        return JsonResponse({'error': 'Invalid project ID'})


@login_required
def deploy(request, pk=0):
    status, access_token, gl = get_gitlab_token(request)
    if not status:
        return redirect("account_logout")
    
    project_id = request.POST.get('project')
    branch = request.POST.get('branch')
    internal_port = request.POST.get('internal_port')
    docker_image = request.POST.get('docker_image')
    dockerfile = request.POST.get('dockerfile')
    project_name = ""
    project_url = ""

    if pk!=0:
        try:
            instance = RunningInstance.objects.get(pk=pk)
            project_name=instance.repo_name
            branch=instance.branch
            docker_image=instance.app_docker_image
            dockerfile=instance.app_dockerfile
            internal_port=instance.internal_port
            deployment_id=instance.deployment_id
            project_url=instance.project_url
        except:  # pylint: disable=bare-except
            return redirect('gitlab_social_dashboard')
    else:
        project_name = gl.projects.get(project_id).name.lower().replace(" ", "-")
        project_url = gl.projects.get(project_id).http_url_to_repo
    group_name = "IRIS-NITK"

    # external_port = find_free_port()
    try:
        instance = RunningInstance.objects.get(
            social='git.iris',
            organisation=group_name,
            repo_name=project_name,  # add this in template
            branch=branch
        )
        instance.owner = request.user.username
        instance.update_time = time.time()
        instance.internal_port = internal_port
        # instance.exposed_port = external_port
        instance.status = RunningInstance.STATUS_PENDING
        instance.app_docker_image = docker_image
        instance.app_dockerfile = dockerfile
        instance.save()

    except ObjectDoesNotExist:
        deployment_id = generate_deployment_id(group_name, project_name, branch, settings.STAGING_CONF['DOMAIN'], settings.STAGING_CONF['SUBDOMAIN_PREFIX'])
        app_container_name = get_app_container_name(settings.STAGING_CONF['PREFIX'], deployment_id)
        db_container_name = get_db_container_name(settings.STAGING_CONF['PREFIX'], deployment_id)
        instance = RunningInstance(
            # exposed_port=external_port,
            social='git.iris',
            organisation=group_name,
            repo_name=project_name,
            branch=branch,
            internal_port=internal_port,
            owner=request.user.username,
            update_time=time.time(),
            status=RunningInstance.STATUS_PENDING,
            deployed_url = f"https://staging-{deployment_id}.iris.nitk.ac.in",
            project_url = project_url,
            app_container_name = app_container_name,
            db_container_name = db_container_name,
            deployment_id = deployment_id,
            app_docker_image = docker_image,
            app_dockerfile = dockerfile,
        )
        instance.save()

    if docker_image == '' or len(docker_image) == 0:
        docker_image = None

    deploy_gitlab_social(
        url=project_url,
        user_name="oauth2",
        group=group_name,
        project=project_name,
        branch=branch,
        internal_port=internal_port,
        deployment_id=deployment_id,
        # external_port=external_port,
        docker_image=docker_image,
        token=access_token,
        dockerfile=dockerfile,
    )
    return redirect('gitlab_social_dashboard')


@login_required
def stop(request, pk, stop_db=False):
    """
    Stops container and deletes instance
    """
    try:
        instance = RunningInstance.objects.get(pk=pk)
    except:  # pylint: disable=bare-except
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    delete_instance(instance, stop_db)
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

@login_required
def stop_with_db(request, pk):
    """
    Stops container , deletes instance and deletes db container 
    """
    return stop(request=request, pk=pk, stop_db=True)


@login_required
def health_check(request, pk):
    res = f"Health Check...\nPK: {pk}\n"
    return HttpResponse(res)

