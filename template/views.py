from django.shortcuts import render, redirect
from django.core.exceptions import ObjectDoesNotExist

from main.models import RunningInstance

from template.models import Template
from template.forms import TemplateForm 
from template import services

from dotenv import load_dotenv
import os, time

from main.tasks.services import clean_up
from main.tasks.findfreeport import find_free_port



load_dotenv()
PREFIX = os.getenv("PREFIX", "dev")
DOMAIN_PREFIX = os.getenv("DOMAIN_PREFIX", "staging")
DOMAIN = os.getenv("DOMAIN","iris.nitk.ac.in")

def dashboard(request):
    """
    Dashboard to view deployed sites from templates (or other options)
    """
    return render(
        request,
        "template/dashboard.html",
        context = {
            "instances": RunningInstance.objects.all()
        }
    )


def list(request):
    """
    List of Templates available
    """
    templates = Template.objects.all()
    return render(
        request,
        "template/list.html",
        context = {
            "templates": templates
        }
    )


def form(request):
    """
    Form to add a new Template
    """
    if request.method == "POST":
        form = TemplateForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("template_dashboard")
    else:
        form = TemplateForm()
    return render(
        request,
        "template/form.html",
        context={
            "form": form
        }
    )

def update(request, pk):
    """
    Update an exisiting Template
    """
    template = Template.objects.get(pk=pk)
    if request.method == "POST":
        form = TemplateForm(request.POST, instance=template)
        if form.is_valid():
            form.save()
            return redirect("template_list")
    else:
        form = TemplateForm(instance=template)
    return render(
        request,
        "template/form.html",
        context={
            "form": form
        }
    )


def delete(request, pk):
    """
    Delete the template
    """
    template = Template.objects.get(pk=pk)
    template.delete()
    return redirect("template_list") 

def duplicate(request, pk):
    """
    Duplicate existing template
    """
    if request.method == 'POST':
        template = Template.objects.get(pk = pk)
        duplicate_template = Template.objects.create(
            name = template.name + "_copy",
            social_type = template.vcs,
            organisation_or_user = template.user_name,
            git_repo_url = template.git_url,
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
    return redirect("template_list")
    

def stop(request, pk):
    """
    Stops container and deletes instance
    """
    instance = RunningInstance.objects.get(pk=pk)
    container_name = f"{PREFIX}_{instance.organisation.lower()}_{instance.repo_name.lower()}_{instance.branch.lower()}"

    # stop container
    clean_up(
        org_name = instance.organisation,
        repo_name = instance.repo_name,
        remove_container = container_name
    )

    # delete the object from database
    instance.delete()
    return redirect("template_dashboard")

def deploy(request, pk):  
    """
    Deploy service from the template
    """ 
    if request.method == "POST":
        template = Template.objects.get(pk=pk)
        external_port = find_free_port()
        try:
            instance = RunningInstance.objects.get(
                social = template.vcs, 
                organisation = template.user_name,
                repo_name = template.repo_name, # add this in template
                branch= template.default_branch
            )
            instance.owner = request.user.username 
            instance.update_time = time.time()
            instance.exposed_port = external_port
            instance.status = RunningInstance.STATUS_PENDING
            instance.save()

        except ObjectDoesNotExist:
            instance = RunningInstance(
                exposed_port = external_port,
                social = template.vcs,
                organisation = template.user_name, 
                repo_name = template.repo_name, 
                branch = template.default_branch, 
                owner = request.user.username, 
                update_time = time.time(), 
                status = RunningInstance.STATUS_PENDING
            )
            instance.save()
       
        services.deploy.delay(
            url = template.git_url, 
            repo_name = template.repo_name, 
            vcs = template.vcs, 
            branch = template.branch, 
            external_port = external_port, 
            interal_port = template.internal_port, 
            access_token = template.access_token, 
            docker_image = template.docker_image, 
            docker_network = template.docker_network, 
            dockerfile_path = template.dockerfile_path, 
            docker_volumes = template.docker_volumes, 
            docker_env_variables = template.docker_env_vars
        )

    return redirect("template_dashboard")

AUTH_HEADER = os.getenv("AUTH_HEADER")
def health_check(request, pk):
    instance = RunningInstance.objects.get(pk = pk)
    if instance.social == "git.iris":
        url = f"https://{DOMAIN_PREFIX}-{instance.branch.lower()}.{DOMAIN}"
    else:
        url = f"https://{DOMAIN_PREFIX}-{instance.organisation.lower()}-{instance.repo_name.lower()}-{instance.branch.lower()}.{DOMAIN}"

    status = services.health_check(url=url, auth_header=f"basic {AUTH_HEADER}")
    if status:
        instance.status = RunningInstance.STATUS_SUCCESS
    else:
        instance.status = RunningInstance.STATUS_PENDING

    instance.save()
    return redirect("template_dashboard")
    