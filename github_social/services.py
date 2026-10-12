"""
Services for GitHub-based deployments.
"""
from github import Github
from allauth.socialaccount.models import SocialToken
from django.conf import settings

from main.services import deploy as deploy_template
from main.utils.helpers import get_app_container_name, get_db_container_name


def deploy(url,
           user_name,
           group,
           project,
           branch,
           internal_port,
           deployment_id,
           docker_image,
           token,
           dockerfile=None,
           ):
    """Create a deployment task for a GitHub repository."""
    db_env = {
        "MYSQL_ROOT_PASSWORD": settings.STAGING_CONF['DB_DEFAULT_ROOT_PASSWORD'],
        "MYSQL_DATABASE": settings.STAGING_CONF['DB_DEFAULT_DATABASE'],
        "MYSQL_USER": settings.STAGING_CONF['DB_DEFAULT_USER'],
        "MYSQL_PASSWORD": settings.STAGING_CONF['DB_DEFAULT_PASSWORD'],
    }

    app_container_name = get_app_container_name(settings.STAGING_CONF['PREFIX'], deployment_id)
    db_container_name = get_db_container_name(settings.STAGING_CONF['PREFIX'], deployment_id)
    app_env = {
        "RAILS_ENV": "development",
        "DEV_DB_HOST": db_container_name,
    }
    post_deploy_scripts = {
        'commands': [
            ["python3", settings.STAGING_CONF['NGINX_PYTHON_ADD_CONFIG_SCRIPT'],
             str(internal_port), str(settings.STAGING_CONF['SUBDOMAIN_PREFIX']), str(deployment_id), str(app_container_name)],
            ["docker", "exec", "nginx-stagingserver", "nginx", "-s", "reload"]
        ],
        'msg_error': "Error while adding nginx config",
        'msg_success': "Nginx config added successfully",
    }

    db_container = {
        'image': settings.STAGING_CONF['DOCKER_DB_IMAGE'],
        'env_variables': db_env,
        'container_name': db_container_name,
        'dump_path': None,
        'bind_path': None,
        'volume_name': None,
    }
    app_container = {
        'image': docker_image,
        'network': settings.STAGING_CONF['DEPLOYMENT_DOCKER_NETWORK'],
        'container_name': app_container_name,
        'env_variables': app_env,
        'volumes': None,
        'dockerfile_path': dockerfile,
    }

    return deploy_template.delay(
        url=url,
        user_name=user_name,
        repo_name=project,
        org_name=group,
        vcs="github",
        branch=branch,
        deployment_id=deployment_id,
        internal_port=internal_port,
        access_token=token,
        docker_app=app_container,
        docker_db=db_container,
        post_deploy_scripts=post_deploy_scripts,
    )


def get_github_token(request):
    """Return the GitHub OAuth token and a PyGithub client for the current user."""
    try:
        social_token = SocialToken.objects.get(
            account__user=request.user,
            account__provider='github',
        )
    except SocialToken.DoesNotExist:
        return False, None, None

    token = social_token.token
    github_client = Github(token)
    try:
        github_client.get_user().login
    except Exception:  # pragma: no cover - network validation only
        return False, None, None
    return True, token, github_client
