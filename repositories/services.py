import json, os
from celery import shared_task
from io import StringIO

from django.core import serializers

from main.utils.helpers import initiate_logger
from main.services import pull_git_changes
from main.utils.helpers import exec_commands
from main.models import RunningInstance

from repositories.models import Repository

from template.services import deploy as deploy_template

PATH_TO_HOME_DIR = os.getenv("PATH_TO_HOME_DIR")  # Path to home directory
NGINX_PYTHON_ADD_CONFIG_SCRIPT_IRIS = os.getenv("NGINX_PYTHON_ADD_CONFIG_SCRIPT_IRIS", None) # Path to nginx add config script
SUBDOMAIN_PREFIX = os.getenv("SUBDOMAIN_PREFIX", "staging")  # Prefix for domain name
DEPLOYMENT_DOCKER_NETWORK = os.getenv("DEPLOYMENT_DOCKER_NETWORK", "IRIS") # Docker network for iris containers

@shared_task(bind=True)
def create(self, repo_git_url,
           access_token,
           repo_username,
           repo_name,
           deployer,
           repository_pk):
    """
    clone and setup new repository instance
    """
    log_file_path = f"{PATH_TO_HOME_DIR}/logs/repositories/{deployer}/{repository_pk}"
    clone_path = f"{PATH_TO_HOME_DIR}/repositories/{deployer}/{repository_pk}"
    result, logs = pull_git_changes(
        url=repo_git_url,
        user_name=repo_username,
        org_name=deployer,
        repo_name=repo_name,
        branch_name=None,
        token=access_token,
        log_file_path=log_file_path,
        clone_path=clone_path
    )
    repository = Repository.objects.get(pk=repository_pk)
    if not result:
        repository.status = repository.STATUS_ERROR
        repository.save()
        return False
    repository.status = repository.STATUS_SUCCESS
    repository.save()
    return True

def get_branches(deployer, repository_pk, repo_name, repo_dir=None):
    """
    gets all remote branches list of a repository
    """
    if not repo_dir:
        repo_dir = f"{PATH_TO_HOME_DIR}/repositories/{deployer}/{repository_pk}/DEFAULT_BRANCH/{repo_name}"

    temp_logging_text=""
    common_args = {
    "cwd": repo_dir,
    "logger": temp_logging_text,
    "err": "repo branch list fetch failed",
    "logger_not_file": True,
    "print_stderr": True
    }
    status, remote = exec_commands(
        commands=[
            ["git", "remote", "show"]
        ],
        **common_args
    )
    if not status:
        return False, temp_logging_text
    remote = remote.strip().split('\n')[0]
    status, result = exec_commands(
        commands=[
            ["git", "fetch", "--prune", remote]
        ],
        **common_args
    )
    if not status:
        return False, temp_logging_text
    status, result = exec_commands(
        commands=[
            ['git', 'branch', '-r']
        ],
        **common_args
    )
    if not status:
        return False, temp_logging_text
    result = result.strip().split('\n')
    # Extract and clean the branch names (remove "origin/")
    branch_names = [branch.strip().replace(f'{remote}/', '') for branch in result if not branch.strip().startswith('HEAD ->')]
    result = []
    for branch in branch_names:
        if branch.startswith("HEAD ->"):
            continue
        result.append(branch)
    return True, result

def deploy(branch,
           repository,
           instance,
           ):
    """
    deploys a specific branch of a repository
    """
    # repository = Repository.objects.get(pk=repository_pk)
    # instance = RunningInstance.objects.get(pk=instance_pk)
    app_env_vars = instance.app_env_vars if instance.app_env_vars else {}  
    db_env_vars = instance.db_env_vars if instance.db_env_vars else {} 
    post_deploy_scripts = {
        'commands': [
            ["python3", NGINX_PYTHON_ADD_CONFIG_SCRIPT_IRIS,
            str(repository.internal_port), str(SUBDOMAIN_PREFIX), str(instance.deployment_id), str(instance.app_container_name)],
            ["docker", "exec", "nginx-stagingserver", "nginx", "-s", "reload"]
            ],
        'msg_error': "Error while adding nginx config",
        'msg_success': "Nginx config added successfully"
    }
    db_container = {
        'image':instance.db_docker_image,
        'env_variables':db_env_vars,
        'container_name':instance.db_container_name,
        'dump_path': None,
        'bind_path':None,
        'volume_name': None
    }
    app_container = {
        'image': None,
        'network': DEPLOYMENT_DOCKER_NETWORK,
        'container_name': instance.app_container_name,
        'env_variables': app_env_vars,
        'volumes': None,
        'dockerfile_path': instance.dockerfile_path,
    }

    log_file_path = f"{PATH_TO_HOME_DIR}/logs/repositories/{repository.deployer.username}/{repository.pk}"
    clone_path = f"{PATH_TO_HOME_DIR}/repositories/{repository.deployer.username}/{repository.pk}"
    return deploy_template.delay(
        url=repository.repo_git_url,
        user_name=repository.repo_username,
        repo_name=instance.repo_name,
        org_name=repository.deployer.username,
        vcs="repositories",
        branch=branch,
        deployment_id=instance.deployment_id,
        internal_port=instance.internal_port,
        access_token=repository.access_token,
        docker_app=app_container,
        docker_db=db_container,
        post_deploy_scripts=post_deploy_scripts,
        log_file_path=log_file_path,
        clone_path=clone_path,
    )