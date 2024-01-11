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
DEFAULT_NETWORK = os.getenv("DEFAULT_NETWORK", "IRIS")


@shared_task(bind=True)
def deploy(self,
           url,
           user_name,
           org_name,
           repo_name,
           vcs,
           branch,
        #    external_port,
           hashed_branch,
           internal_port=80,
           access_token=None,
           docker_app=None,
           docker_db=None,
           post_deploy_scripts=None,
           pre_deploy_scripts=None
           ):
    """
    Pulls changes, builds/pulls docker image, starts container, configure NGINX
    """
    # logfile where logs for this deployment are stored
    log_file = f"{PATH_TO_HOME_DIR}/logs/{org_name}/{repo_name}/{branch}/{branch}.txt"
    logger = initiate_logger(log_file)

    # closing existing container if it exists.
    app_container_name = docker_app.get(
        'container_name', 
        f"{PREFIX}_{repo_name.lower()[0:4]}_{branch.lower()[0:10]}{hashed_branch}")
    stop_containers(container_name=app_container_name, logger=logger)
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

    # Building docker image
    docker_image = docker_app.get('image', None)
    cwd = f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch}/{repo_name}/"
    if not docker_image:
        pretty_print(logger, "No Docker image provided")
        pretty_print(logger, f"Building image with {docker_app.get('dockerfile_path', 'Dockerfile')} ...")

        # building docker image and tagging it
        docker_image = f"{PREFIX}_{org_name.lower()}_{repo_name.lower()}_{branch.lower()}"
        exec_dockerfile = []
        if docker_app.get('dockerfile_path', None):
            exec_dockerfile = ["-f", f"./{docker_app.get('dockerfile_path', '')}"]
            print(exec_dockerfile)
        elif os.path.exists(f"{cwd}/Dockerfile.Staging"):
                exec_dockerfile = ["-f", f"./Dockerfile.Staging"]
        status, err = exec_commands(commands=[
            ['docker', 'build', '--tag', docker_image, *exec_dockerfile, '.']
        ],
            logger=logger,
            cwd=cwd, # Not sure rn
            err=f"Error while building docker image {docker_image}",
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

    # Creating docker network for the container
    network_name=docker_app.get('network', DEFAULT_NETWORK)
    if network_name:
        pretty_print(logger, f"Checking if the docker network {network_name} exists.")
        inspect_network = run(
            ["docker", "network", "inspect", network_name],
            stderr=PIPE,
            stdout=PIPE,
            check=False
        )
        if inspect_network.returncode == 0:
            pretty_print(logger, f"Docker network {network_name} already exists")
        else:
            pretty_print(logger, f"Docker network {network_name} does not exist, creating it")
            status, err = exec_commands(
                commands=[['docker', 'network', 'create', network_name]],
                logger=logger,
                err=f"Error creating docker network {network_name}",
                print_stderr=False
            )
            if status:
                pretty_print(logger,f"Successfully created docker network {network_name}")
            else:
                return status, err

    # start db container if required
    if docker_db:
        pretty_print(logger, "checking for existing database container")
        docker_db_container_name = docker_db.get('container_name',
                                                  f"db_{app_container_name}")

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
                db_image=docker_db.get('image',None),
                db_name=docker_db_container_name,
                db_dump_path=docker_db.get('dump_path',None),
                db_env_variables=docker_db.get('env_variables',None),
                volume_bind_path=docker_db.get('bind_path',None),
                volume_name=docker_db.get('volume_name',None),
                network_name=network_name,
            )

            if not result:
                return False, f"Failed to start {docker_db_container_name}, {logs}"

    # Execute Pre Deployment scripts
    if pre_deploy_scripts:
        pretty_print(logger, "Executing pre deployment Scripts")
        status, err = exec_commands(
            commands=pre_deploy_scripts.get('commands',[]),
            logger=logger,
            err=pre_deploy_scripts.get("msg_error",""),
            print_stderr=True
        )
        if status:
            pretty_print(logger,pre_deploy_scripts.get("msg_success",""))

    # start the container
    pretty_print(logger, f"Starting app container -> {app_container_name}")
    pretty_print(logger, f"Base image : {docker_image}")

    result, logs = start_container(
        image_name=docker_image,
        org_name=org_name,
        repo_name=repo_name,
        branch_name=branch,
        container_name=app_container_name,
        # external_port=external_port,
        internal_port=internal_port,
        volumes=docker_app.get('volumes', None),
        enviroment_variables=docker_app.get('env_variables', None),
        docker_network=network_name
    )

    if not result:
        pretty_print(
            logger, f"Error while starting container : {app_container_name}")
        pretty_print(logger, logs)
        logger.close()
        return False, logs

    if not result:
        pretty_print(logger, " ⚠️ Error while starting container")
        pretty_print(logger, logs)
        logger.close()
        return False, logs
    # to execute commands after deployments, like to setup nginx config.
    if post_deploy_scripts:
        pretty_print(logger, "Executing post deployment Scripts")
        status, err = exec_commands(post_deploy_scripts.get('commands',[]),
            logger=logger,
            err=post_deploy_scripts.get('msg_error',""),
            print_stderr=True
        )
        if status:
            pretty_print(logger, post_deploy_scripts.get('msg_success',""))

    pretty_print(logger, "Successully deployed 🥳")

    return True, logs  # log will be container id
