"""
main functions required for the staging server to work!!!
"""
import os
import datetime
import socket
from contextlib import closing
import requests
from dotenv import load_dotenv
from main.utils.helpers import pretty_print, initiate_logger
from main.utils.helpers import exec_commands, delete_directory

load_dotenv()
# environment variables are now loaded

PREFIX = os.getenv("PREFIX", "iris")
PATH_TO_HOME_DIR = os.getenv("PATH_TO_HOME_DIR")
NGINX_ADD_CONFIG_SCRIPT_IRIS = os.getenv("NGINX_ADD_CONFIG_SCRIPT_IRIS_PATH")
NGINX_REMOVE_CONFIG_SCRIPT = os.getenv("NGINX_REMOVE_SCRIPT")
DOCKER_IMAGE = os.getenv("BASE_IMAGE")
DOCKER_DB_IMAGE = os.getenv("DOCKER_DB_IMAGE", "mysql:5.7")
IRIS_DOCKER_NETWORK = os.getenv("IRIS_DOCKER_NETWORK", "IRIS")
DOMAIN_PREFIX = os.getenv("DOMAIN_PREFIX", "staging")
DOMAIN = os.getenv("DOMAIN", "iris.nitk.ac.in")
DEFAULT_NETWORK = os.getenv("DEFAULT_NETWORK", "IRIS")


def find_free_port():
    """
    Finds a free port on the host machine
    """
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


def health_check(url, auth_header):
    """
    Checking uptime status of site, uses auth header
    """
    try:
        if auth_header:
            response = requests.get(
                url, headers={"Authorization": auth_header}, timeout=5)
        else:
            response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return True
        else:
            return False
    except:  # pylint: disable=bare-except
        return False


def clone_repository(url='git.iris.nitk.ac.in',
                     clone_url="",
                     user_name=None,
                     token=None,
                     org_name=None,
                     repo_name=None,
                     branch_name='DEFAULT_BRANCH'
                     ):
    """
    Clones the Repository if it doesn't exist.
    """
    temp_logging_text = ""
    # Create Org directory if it doesn't exist
    if not os.path.exists(f"{PATH_TO_HOME_DIR}/{org_name}"):
        temp_logging_text = f'\n{datetime.datetime.now()} : Organization {org_name} does not exist locally, creating it\n'
        os.makedirs(f"{PATH_TO_HOME_DIR}/{org_name}")

    # org exists , repo does not exist , could be a new repo , so clone it
    os.makedirs(
        f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/DEFAULT_BRANCH")
    temp_logging_text += f'\n{datetime.datetime.now()} : Repository {repo_name} does not exist locally, cloning it\n'

    parent_dir = f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/DEFAULT_BRANCH"
    local_dir = os.path.join(parent_dir, repo_name)

    status, err = exec_commands(commands=[
        ['git', 'clone', clone_url, local_dir]
    ],
        cwd=f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/",
        logger=temp_logging_text,
        err="Git clone failed",
        logger_not_file=True,
        print_stderr=True
    )
    if not status:
        return False, err

    os.makedirs(f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}")

    log_file = (
        f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/{branch_name}.txt"
    )

    logger = initiate_logger(log_file)

    logger.write(temp_logging_text)
    logger.close()
    return True, ""


def pull_git_changes(vcs,
                     url='git.iris.nitk.ac.in',
                     user_name=None,
                     token=None,
                     org_name=None,
                     repo_name=None,
                     branch_name='DEFAULT_BRANCH',
                     default_branch_name='master'):
    """
    Pulls the latest changes from the git repo, if the repo is not present, then it clones the repo
    """
    if not (org_name and repo_name):
        return False, "Org name and repo name are required\n"
    clone_url = f'https://{user_name}:{token}@{url}/{org_name}/{repo_name}.git'
    # Check if repository exists
    if not os.path.exists(f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/DEFAULT_BRANCH/{repo_name}/.git"):
        status, err = clone_repository(
            url=url,
            clone_url=clone_url,
            user_name=user_name,
            token=token,
            org_name=org_name,
            repo_name=repo_name,
            branch_name=branch_name,
        )
        if not status:
            return False, err

    log_file = (
        f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/{branch_name}.txt"
    )

    # Initiates Logger and also creates branch_name directory if it doesn't exist.
    logger = initiate_logger(log_file)

    # Copy repository to branch's folder.
    status, err = exec_commands(commands=[
        ['cp', '-r', f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/DEFAULT_BRANCH/{repo_name}/.",
         f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/{repo_name}"]
    ],
        cwd=f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/DEFAULT_BRANCH/{repo_name}",
        logger=logger,
        err=f"Error while copying Repostiry from base directory to {branch_name}'s directory",
        print_stderr=True
    )
    if not status:
        logger.close()
        return False, err
    pretty_print(
        logger, f"Successfully copied the branch {branch_name} to its directory")

    # Branch exists , pull latest changes
    pretty_print(
        logger, f"Pulling latest changes from branch {branch_name}")

    status, err = exec_commands(commands=[
        ["git", "checkout", "--force", default_branch_name],
        ["git", "pull", clone_url],
        ["git", "checkout", branch_name],
        ["git", "pull", clone_url]

    ],
        cwd=f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/{repo_name}",
        logger=logger,
        err=f"Error while pulling latest changes from branch {branch_name}",
        print_stderr=True
    )
    if not status:
        logger.close()
        return False, err

    pretty_print(
        logger,
        f"Successfully pulled all the latest changes from branch {branch_name} to base directory."
    )

    logger.close()
    return True, ""


def start_container(image_name,
                    org_name,
                    repo_name,
                    branch_name,
                    container_name,
                    external_port,
                    internal_port,
                    volumes=None,
                    enviroment_variables=None,
                    docker_network=DEFAULT_NETWORK):
    """
    Generalised function to start a container for any service
    """

    command = ["docker", "run", "-d"]

    # TO DO : Add support for multiple ports to be exposed
    # assert len(external_port) == len(internal_port),
    # "Number of external ports and internal ports should be equal"

    # for ext_port, int_port in zip(external_port, internal_port):
    #     command.extend(["-p", f"{ext_port}:{int_port}"])

    command.extend(["-p", f"{external_port}:{internal_port}"])
    if volumes:
        for src, dest in volumes.items():
            command.extend(["-v", f"{src}:{dest}"])
    if enviroment_variables:
        for k, v in enviroment_variables.items():
            command.extend(["--env", f"{k}={v}"])
    if container_name:
        command.extend(["--name", container_name])
    if docker_network:
        command.extend(["--network", docker_network])

    command.extend([image_name])
    logger = ""
    status, result = exec_commands(commands=[
        command
    ],
        cwd=None,
        logger=logger,
        err="Error Deploying Container",
        print_stderr=True,
        logger_not_file=True
    )
    if not status:
        return False, result
    return True, result


def start_db_container(db_image,
                       db_name,
                       db_dump_path,
                       volume_name,
                       volume_bind_path,
                       db_env_variables,
                       network_name
                       ):
    """
    starts db container.
    """
    command = ["docker", "run"]
    if db_name:
        command.extend(["--name", db_name])
    if db_dump_path:
        command.extend(["-v", f"{db_dump_path}:/docker-entrypoint-initdb.d/"])
    if volume_name and volume_bind_path:
        command.extend(["-v", f"{volume_name}:{volume_bind_path}"])
    if db_env_variables:
        for key, value in db_env_variables.items():
            command.extend(["--env", f"{key}={value}"])
    if network_name:
        command.extend(["--network", network_name])
    command.extend(["--detach", "--rm", db_image])

    # execute the start db container command
    status, result = exec_commands(commands=[
        command
    ],
        cwd=None,
        err="Error starting database container.",
        print_stderr=True,
        logger_not_file=True
    )
    if not status:
        return False, result
    return True, result


def clean_up(org_name,
             repo_name,
             branch_name=None,
             remove_container=False,
             remove_volume=False,
             remove_network=False,
             remove_image=False,
             remove_branch_dir=False,
             remove_all_dir=False,
             remove_user_dir=False,
             remove_nginx_conf=True):
    """
    Remove all the containers, volumes, networks and images related to the branch
    """
    errors=""
    cleanup_status=True

    if branch_name:
        logger = initiate_logger(
            f"{PATH_TO_HOME_DIR}/logs/{org_name}/{repo_name}/{branch_name}/{branch_name}.txt")
    else:
        logger = initiate_logger(
            f"{PATH_TO_HOME_DIR}/logs/{org_name}/{repo_name}/{repo_name}.txt")

    if remove_container:
        pretty_print(logger,
                     "Removing the container and nginx config."
                     )
        status, err = exec_commands(commands=[
            ["docker", "rm", "-f", remove_container]
        ],
            logger=logger,
            err="Error deleting the container",
            print_stderr=True
        )
        if status:
            pretty_print(logger,
                     "Successfully stopped and deleted the container."
                     )
            errors= errors + err +"\n"
            cleanup_status=False

    if remove_nginx_conf:
        pretty_print(logger,
                     "Removing the nginx config."
                     )
        status, err = exec_commands(commands=[
            ["sudo", "bash", NGINX_REMOVE_CONFIG_SCRIPT, org_name,
             repo_name, branch_name]
        ],
            logger=logger,
            err="Error deleting the nginx config",
            print_stderr=True
        )
        if status:
            pretty_print(logger,
                     "Successfully deleted the nginx config."
                     )
            errors= errors + err +"\n"
            cleanup_status=False

    if remove_volume:
        status, err = exec_commands(commands=[
            ["docker", "volume", "rm", remove_volume]
        ],
            logger=logger,
            err="Error deleting the volume.",
            print_stderr=True
        )
        if status:
            pretty_print(logger,
                     "Successfully deleted the docker volume."
                     )
            errors= errors + err +"\n"
            cleanup_status=False

    if remove_network:
        status, err = exec_commands(commands=[
            ["docker", "network", "rm", remove_network]
        ],
            logger=logger,
            err="Error deleting the docker network.",
            print_stderr=True
        )
        if status:
            pretty_print(logger,
                     "Successfully deleted the docker network."
                     )
            errors= errors + err +"\n"
            cleanup_status=False
        

    if remove_image:
        status, err = exec_commands(commands=[
            ["docker", "image", "rm", remove_image]
        ],
            logger=logger,
            err="Error deleting the docker image.",
            print_stderr=True
        )
        if status:
            pretty_print(logger,
                     "Successfully deleted the docker network."
                     )
            errors= errors + err +"\n"
            cleanup_status=False
        
    if remove_branch_dir:
        pretty_print(logger,
                     "Deleting the branch directory"
                     )
        status, err = delete_directory(
            f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}")
        if status:
            pretty_print(logger,
                     f"Successfully deleted the branch {branch_name} directory."
                     )
            errors= errors + err +"\n"
            cleanup_status=False
        else: pretty_print(logger, err)

    if remove_all_dir:
        status, err = delete_directory(
            f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}")
        if status:
            pretty_print(logger,
                     f"Successfully deleted all directories of the {remove_all_dir} repository."
                     )
            errors= errors + err +"\n"
            cleanup_status=False
        else: pretty_print(logger, err)

    if remove_user_dir:
        status, err = delete_directory(f"{PATH_TO_HOME_DIR}/{org_name}")
        if status:
            pretty_print(logger,
                     f"Successfully deleted {remove_all_dir} user directory."
                     )
            errors= errors + err +"\n"
            cleanup_status=False
        else: pretty_print(logger, err)
    
    pretty_print(logger, f"Clean Up Errors (If Any):\n {errors}")
    pretty_print(logger,
                 "Clean Up Complete"
                 )
    logger.close()
    return cleanup_status, "Clean up complete"
