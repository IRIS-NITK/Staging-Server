"""
Services for other IRIS applications
"""
import os
from dotenv import load_dotenv

import gitlab
from allauth.socialaccount.models import SocialToken
from main.utils.helpers import initiate_logger, get_app_container_name, get_db_container_name
from main.services import deploy as deploy_template
from django.contrib.auth import logout
gitlab_url = __import__('stagingserver').settings.SOCIALACCOUNT_PROVIDERS['gitlab']['GITLAB_URL']
load_dotenv()

PREFIX = os.getenv("PREFIX", "iris")  # Prefix for docker container names
PATH_TO_HOME_DIR = os.getenv("PATH_TO_HOME_DIR")  # Path to home directory
NGINX_PYTHON_ADD_CONFIG_SCRIPT_IRIS = os.getenv("NGINX_PYTHON_ADD_CONFIG_SCRIPT_IRIS", None) # Path to nginx add config script
DOCKER_IMAGE = os.getenv("DOCKER_IMAGE") # Base docker image for iris container
DOCKER_DB_IMAGE = os.getenv("DOCKER_DB_IMAGE", "mysql:5.7") # Base docker image for iris database container
DEPLOYMENT_DOCKER_NETWORK = os.getenv("DEPLOYMENT_DOCKER_NETWORK", "IRIS") # Docker network for iris containers
SUBDOMAIN_PREFIX = os.getenv("SUBDOMAIN_PREFIX", "staging")  # Prefix for domain name
DOMAIN = os.getenv("DOMAIN", "iris.nitk.ac.in")  # Domain name
DB_DEFAULT_USER = os.getenv("DB_DEFAULT_USER", "rootme")
DB_DEFAULT_PASSWORD = os.getenv("DB_DEFAULT_PASSWORD", "password")
DB_DEFAULT_ROOT_PASSWORD = os.getenv("DB_DEFAULT_ROOT_PASSWORD", "password")
DB_DEFAULT_DATABASE = os.getenv("DB_DEFAULT_DATABASE", "staging")

def deploy(url,
           user_name,
           group,
           project,
           branch,
           internal_port,
        #    external_port,
           deployment_id,
           docker_image,
           token,
           dockerfile=None,
           ):
    """
    To deploy other IRIS applications
    """
    # Removing Cleanup to troubleshoot the git pull issue
    # clean_up(
    #     org_name=group,
    #     repo_name=project,
    #     branch_name="DEFAULT_BRANCH",
    #     remove_branch_dir="DEFAULT_BRANCH",
    # )   
    db_env = {
        "MYSQL_ROOT_PASSWORD": DB_DEFAULT_ROOT_PASSWORD,
        "MYSQL_DATABASE": DB_DEFAULT_DATABASE,
        "MYSQL_USER": DB_DEFAULT_USER,
        "MYSQL_PASSWORD": DB_DEFAULT_PASSWORD,
    }

    app_container_name = get_app_container_name(PREFIX, deployment_id)
    db_container_name = get_db_container_name(PREFIX, deployment_id)
    app_env = {
        "RAILS_ENV": "development",
        "DEV_DB_HOST": db_container_name
    }
    post_deploy_scripts = {
        'commands': [
            ["python3", NGINX_PYTHON_ADD_CONFIG_SCRIPT_IRIS,
            str(internal_port), str(SUBDOMAIN_PREFIX), str(deployment_id), str(app_container_name)],
            ["docker", "exec", "nginx-stagingserver", "nginx", "-s", "reload"]
            ],
        'msg_error': "Error while adding nginx config",
        'msg_success': "Nginx config added successfully"
    }

    db_container = {
        'image':DOCKER_DB_IMAGE,
        'env_variables':db_env,
        'container_name':db_container_name,
        'dump_path': None,
        'bind_path':None,
        'volume_name': None
    }
    app_container = {
        'image': docker_image,
        'network': DEPLOYMENT_DOCKER_NETWORK,
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
        vcs="git.iris",
        branch=branch,
        # external_port=external_port,
        deployment_id=deployment_id,
        internal_port=internal_port,
        access_token=token,
        docker_app=app_container,
        docker_db=db_container,
        post_deploy_scripts=post_deploy_scripts
    )

def get_gitlab_token(request):
    """
    gives gitlab token and gitlab connection object I guess
    """
    try: 
        social_token = SocialToken.objects.get(account__user=request.user, account__provider='gitlab')
    except SocialToken.DoesNotExist:
        # means our user was logged in via username and password so they can stay authenticated
        return False, None, None
    gl_access_token = social_token.token
    gl = gitlab.Gitlab(
        url=gitlab_url,
        oauth_token=gl_access_token
    )
    try:
        # Authenticate the GitLab client
        gl.auth()
    except:  # pylint: disable=bare-except
        return False, None, None
    return True, gl_access_token, gl
