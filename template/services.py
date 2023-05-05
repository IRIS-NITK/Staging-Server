import os
import datetime
import requests

from subprocess import PIPE, run
from celery import shared_task
from dotenv import load_dotenv

from main.services import pull_git_changes, start_container
from main.services import start_db_container, stop_containers
from main.utils.helpers import pretty_print, initiate_logger, exec_commands

load_dotenv()

PREFIX = os.getenv("PREFIX", "iris_staging")
PATH_TO_HOME_DIR = os.getenv("PATH_TO_HOME_DIR")
NGINX_ADD_CONFIG_SCRIPT = os.getenv("NGINX_ADD_CONFIG_SCRIPT_PATH")
NGINX_REMOVE_CONFIG_SCRIPT = os.getenv("NGINX_REMOVE_SCRIPT")
DEFAULT_NETWORK = os.getenv("DEFAULT_NETWORK", "IRIS")


def pretty_print(file, text):
    file.write(f"{datetime.datetime.now()} : {text}\n")


@shared_task(bind=True)
def deploy(self,
           url,
           user_name,
           org_name,
           repo_name,
           vcs,
           branch,
           external_port,
           internal_port=80,
           access_token=None,
           docker_image=None,
           docker_network=DEFAULT_NETWORK,
           dockerfile_path=None,
           docker_volumes={},
           docker_env_variables={},
           docker_db_image=None,
           docker_db_volume_name=None,
           docker_db_bind_path=None,
           docker_db_env_variables=None,
           docker_db_dump_path=None,
           docker_db_container_name=None,
           ):
    """
    Pulls changes, builds/pulls docker image, starts container, configure NGINX
    """
    # logfile where logs for this deployment are stored
    log_file = f"{PATH_TO_HOME_DIR}/logs/{org_name}/{repo_name}/{branch}/{branch}.txt"
    logger = initiate_logger(log_file)

    # closing existing container if it exists.
    container_name = f"{PREFIX}_{org_name.lower()}_{repo_name.lower()}_{branch.lower()}"
    stop_containers(container_name=container_name, logger=logger)
    logger.close()

    # Pull changes from git based vcs
    result, logs = pull_git_changes(
        url=url,
        user_name=user_name,
        vcs=vcs,
        org_name=org_name,
        repo_name=repo_name,
        branch_name=branch,
        token=access_token
    )

    if not result:
        print(f"git pull failed\n{logs}")

    logger = initiate_logger(log_file)

    if not docker_image:
        pretty_print(logger, "No Docker image provided")
        if not dockerfile_path:
            dockerfile_path=f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch}/{repo_name}/"
        pretty_print(logger, f"Building image from {dockerfile_path} ...")

        # building docker image and tagging it
        docker_image = f"{PREFIX}_{org_name.lower()}_{repo_name.lower()}_{branch.lower()}"
        status, err = exec_commands(commands=[
            ['docker', 'build', '--tag', docker_image, "."]
        ],
            logger=logger,
            cwd=dockerfile_path,
            err=f"Error while building docker image from {dockerfile_path}",
            print_stderr=True
        )
        if status:
            pretty_print(logger,
                         f"Docker image built: {docker_image}"
                         )
        else:
            return False, err
    else:
        pretty_print(logger, f"Docker image {docker_image} already provided.")

    # start db container if required

    if docker_db_image:
        if not docker_db_container_name:
            docker_db_container_name = f"db_{container_name}"

        inspect_container = run(
            ["docker", "container", "inspect", docker_db_container_name],
            stderr=PIPE,
            stdout=PIPE,
            check=False
        )

        if inspect_container.returncode == 0:
            pretty_print(logger, f"{docker_db_container_name} already exists")
        else:
            pretty_print(
                logger, f"Starting database Container : {docker_db_container_name}")

            result, logs = start_db_container(
                db_image=docker_db_image,
                db_name=docker_db_container_name,
                db_dump_path=docker_db_dump_path,
                db_env_variables=docker_db_env_variables,
                volume_bind_path=docker_db_bind_path,
                volume_name=docker_db_volume_name,
                network_name=docker_network,
            )

            if not result:
                return False, f"Failed to start {docker_db_container_name}, {logs}"
        
    # start the container

    pretty_print(logger, f"Starting container -> {container_name}")
    pretty_print(logger, f"Base image : {docker_image}")

    result, logs = start_container(
        image_name=docker_image,
        org_name=org_name,
        repo_name=repo_name,
        branch_name=branch,
        container_name=container_name,
        external_port=external_port,
        internal_port=internal_port,
        volumes=docker_volumes,
        enviroment_variables=docker_env_variables,
        docker_network=docker_network
    )
    if not result:
        pretty_print(
            logger, f"Error while starting container : {container_name}")
        pretty_print(logger, logs)
        logger.close()
        return False, logs
    
    if not result:
        pretty_print(logger, " ⚠️ Error while starting container")
        pretty_print(logger, logs)
        logger.close()
        return False, logs

    # Configure NGINX
    status, err = exec_commands([
        ["sudo", "bash", NGINX_ADD_CONFIG_SCRIPT, str(org_name.lower()), str(
            repo_name.lower()), str(branch.lower()), str(external_port)]
    ],
        logger=logger,
        err="Error while adding nginx config",
        print_stderr=True
    )
    if not status:
        return False, err

    pretty_print(logger, "Nginx config added successfully")
    pretty_print(logger, "Successully deployed 🥳")
    pretty_print(
        logger, f"Visit it on : staging-{org_name.lower()}\
            -{repo_name.lower()}-{branch.lower()}.iris.nitk.ac.in")

    return True, logs  # log will be container id

