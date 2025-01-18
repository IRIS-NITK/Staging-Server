"""
main functions required for the staging server to work!!!
"""
import os
import datetime
import socket
from contextlib import closing
import urllib.parse
import requests
from dotenv import load_dotenv
from main.utils.helpers import pretty_print, initiate_logger, get_db_container_name,get_app_container_name, get_db_container_name
from main.utils.helpers import exec_commands, delete_directory, write_file
from subprocess import PIPE, run
from celery import shared_task
from django.conf import settings
load_dotenv()
# environment variables are now loaded

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


def clone_repository(clone_url="",
                     org_name=None,
                     repo_name=None,
                     branch_name='DEFAULT_BRANCH',
                     clone_path=None,
                     log_file_path=None
                     ):
    """
    Clones the Repository if it doesn't exist.
    """
    if not branch_name:
        branch_name = 'DEFAULT_BRANCH'
    temp_logging_text = ""
    # Create Org directory if it doesn't exist
    clone_path = f"{clone_path}/DEFAULT_BRANCH"
    if not os.path.exists(f"{clone_path}/DEFAULT_BRANCH"):
        temp_logging_text = f'\n{datetime.datetime.now()} : Default branch folder does not exist locally, creating it\n'
        os.makedirs(clone_path, exist_ok=True)

    temp_logging_text += f'\n{datetime.datetime.now()} : Repository {repo_name} does not exist locally, cloning it\n'

    local_dir = os.path.join(clone_path, repo_name)

    status, err = exec_commands(commands=[
        ['git', 'clone', clone_url, local_dir]
    ],
        cwd=clone_path,
        logger=temp_logging_text,
        err="Git clone failed",
        logger_not_file=True,
        print_stderr=True
    )
    if not status:
        return False, err
    if log_file_path is None:
        log_file_path = f"{settings.STAGING_CONF['PATH_TO_HOME_DIR']}/logs/{org_name}/{repo_name}/{branch_name}"
    else:
        log_file_path = f"{log_file_path}/{branch_name}"
    os.makedirs(
        log_file_path, exist_ok=True)

    log_file = (
        f"{log_file_path}/{branch_name}.txt"
    )

    logger = initiate_logger(log_file)

    logger.write(temp_logging_text)
    logger.close()
    return True, ""


def pull_git_changes(url='https://git.iris.nitk.ac.in/',
                     user_name=None,
                     token=None,
                     org_name=None,
                     repo_name=None,
                     branch_name=None,
                     clone_path=None,
                     log_file_path=None):
    """
    Pulls the latest changes from the git repo, if the repo is not present, then it clones the repo
    """
    if not (org_name and repo_name):
        return False, "Org name and repo name are required\n"

    parsed_url = urllib.parse.urlparse(url)
    clone_url = f'{parsed_url.scheme}://{user_name}:{token}@{parsed_url.hostname}{parsed_url.path}'
    # Check if repository exists
    if not clone_path:
        clone_path = f"{settings.STAGING_CONF['PATH_TO_HOME_DIR']}/{org_name}/{repo_name}"
    if not os.path.exists(f"{clone_path}/DEFAULT_BRANCH/{repo_name}/.git"):
        status, err = clone_repository(
            clone_url=clone_url,
            org_name=org_name,
            repo_name=repo_name,
            branch_name=branch_name,
            clone_path=clone_path,
            log_file_path=log_file_path
        )
        if not status:
            return False, err
    if branch_name != None:
        if not log_file_path:
            log_file = (
                f"{settings.STAGING_CONF['PATH_TO_HOME_DIR']}/logs/{org_name}/{repo_name}/{branch_name}/{branch_name}.txt"
            )
        else:
            log_file = f"{log_file_path}/{branch_name}/{branch_name}.txt"
        # Initiates Logger and also creates branch_name directory if it doesn't exist.
        logger = initiate_logger(log_file)
        default_branch_path = f"{clone_path}/DEFAULT_BRANCH/{repo_name}/."
        deploy_branch_path = f"{clone_path}/{branch_name}/{repo_name}"
        os.makedirs(deploy_branch_path, exist_ok=True)
        # Copy repository to branch's folder.
        status, err = exec_commands(commands=[
            ['rm', '-rf', deploy_branch_path],
            ['cp', '-rf', default_branch_path, deploy_branch_path]
        ],
            cwd=None,
            logger=logger,
            err=f"Error while copying Repository from Default branch's directory to {branch_name}'s directory",
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
            ["git", "pull", clone_url],
            ["git", "checkout", branch_name]
        ],
            cwd=f"{clone_path}/{branch_name}/{repo_name}",
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
                    # external_port,
                    internal_port,
                    volumes=None,
                    enviroment_variables=None,
                    docker_network=settings.STAGING_CONF['DEPLOYMENT_DOCKER_NETWORK'],
                    restart_always=True):
    """
    Generalised function to start a container for any service
    """

    command = ["docker", "run", "-d"]

    # TO DO : Add support for multiple ports to be exposed
    # assert len(external_port) == len(internal_port),
    # "Number of external ports and internal ports should be equal"

    # for ext_port, int_port in zip(external_port, internal_port):
    #     command.extend(["-p", f"{ext_port}:{int_port}"])

    # command.extend(["-p", f"{external_port}:{internal_port}"])
    command.extend([f"-expose={internal_port}"])
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
    if restart_always:
        command.extend(["--restart", "always"])
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
                       network_name,
                       restart_always=True
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
    if restart_always:
        command.extend(["--restart", "always"])        
    if network_name:
        command.extend(["--network", network_name])
    command.extend(["--detach", db_image])

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
             branch,
             deployment_id=None,
             branch_name=None,
             remove_container=False,
             remove_volume=False,
             remove_network=False,
             remove_image=False,
             remove_branch_dir=False,
             remove_all_dir=False,
             remove_user_dir=False,
             remove_nginx_conf=True,
             log_file_path=None,
             branch_deploy_path=None,
             repo_path=None,
             remove_repo=False,
             ):
    """
    Remove all the containers, volumes, networks and images related to the branch
    """
    errors = ""
    cleanup_status = True
    if not log_file_path:
        if branch_name:
            logger = initiate_logger(
                f"{settings.STAGING_CONF['PATH_TO_HOME_DIR']}/logs/{org_name}/{repo_name}/{branch_name}/{branch_name}.txt")
        else:
            logger = initiate_logger(
                f"{settings.STAGING_CONF['PATH_TO_HOME_DIR']}/logs/{org_name}/{repo_name}/{repo_name}.txt")
    else:
        logger = initiate_logger(log_file_path)

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
        else:
            pretty_print(logger, err)

    if remove_nginx_conf:
        pretty_print(logger,
                     "Removing the nginx config."
                     )
        status, err = exec_commands(commands=[
            ["python3", settings.STAGING_CONF['NGINX_PYTHON_REMOVE_SCRIPT_IRIS'], 
             str(deployment_id)],
            ["docker", "exec", "nginx-stagingserver", "/bin/sh", "rm", f"etc/nginx/conf.d/dev-{deployment_id}.conf"],
            ["docker", "exec", "nginx-stagingserver", "nginx", "-s", "reload"]
        ],
            logger=logger,
            err="Error deleting the nginx config",
            print_stderr=True
        )
        if status:
            pretty_print(logger,
                         "Successfully deleted the nginx config."
                         )
        else:
            pretty_print(logger, err)

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
        else:
            pretty_print(logger, err)

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
        else:
            pretty_print(logger, err)

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
        else:
            pretty_print(logger, err)

    if remove_branch_dir:
        if not branch_deploy_path:
            branch_deploy_path = f"{settings.STAGING_CONF['PATH_TO_HOME_DIR']}/{org_name}/{repo_name}/{branch_name}"
        pretty_print(logger,
                     "Deleting the branch directory"
                     )
        status, err = delete_directory(
            branch_deploy_path)
        if status:
            pretty_print(logger,
                         f"Successfully deleted the branch {branch_name} directory."
                         )
        else:
            pretty_print(logger, err)

    if remove_repo:
        pretty_print(logger,
                     "Deleting the repo directory"
                     )
        status, err = delete_directory(
            repo_path)
        if status:
            pretty_print(logger,
                         f"Successfully deleted the {repo_name}'s directory."
                         )
        else:
            pretty_print(logger, err)

    if remove_all_dir:
        status, err = delete_directory(
            f"{settings.STAGING_CONF['PATH_TO_HOME_DIR']}/{org_name}/{repo_name}")
        if status:
            pretty_print(logger,
                         f"Successfully deleted all directories of the {remove_all_dir} repository."
                         )
        else:
            pretty_print(logger, err)

    if remove_user_dir:
        status, err = delete_directory(f"{settings.STAGING_CONF['PATH_TO_HOME_DIR']}/{org_name}")
        if status:
            pretty_print(logger,
                         f"Successfully deleted {remove_all_dir} user directory."
                         )
        else:
            pretty_print(logger, err)

    pretty_print(logger, f"Clean Up Errors (If Any):\n {errors}")
    pretty_print(logger,
                 "Clean Up Complete"
                 )
    logger.close()
    return cleanup_status, "Clean up complete"


def clean_logs(org_name, repo_name, branch_name, log_file_path=None):
    """
    Cleans up the main log and archives the text.
    """
    if not log_file_path:
        log_dir = f"{settings.STAGING_CONF['PATH_TO_HOME_DIR']}/logs/{org_name}/{repo_name}/{branch_name}/"
        log_file_path = f"{log_dir}/{branch_name}.txt"
    else:
        log_dir = os.path.dirname(log_file_path)
    arhive_file_path = f"{log_dir}/archive.txt"
    if os.path.isfile(log_file_path):
        with open(log_file_path, "r", encoding='UTF-8') as log_file, \
                open(arhive_file_path, "a", encoding='UTF-8') as arhive_file:
            arhive_file.write(log_file.read())
        # delete the source file
        os.remove(log_file_path)
    return True, ""


def stop_containers(container_name, logger):
    """
    stops a container with container_name provided
    """
    pretty_print(logger,
                 f"Checking if there is any existing container {container_name}")
    inspect_container = run(
        ["docker", "container", "inspect", container_name],
        stderr=PIPE,
        stdout=PIPE,
        check=False
    )

    if inspect_container.returncode == 0:
        pretty_print(logger, f"Container {container_name} already exists")
        pretty_print(
            logger, f"Stopping and removing existing container {container_name}")
        status, err = exec_commands(commands=[
                                    ["docker", "rm", "-f", container_name]],
                                    logger=logger,
                                    err="Error while removing existing container",
                                    print_stderr=True
                                    )
        if not status:
            return False, err
        pretty_print(logger, f"Existing container {container_name} removed\n")
    else:
        pretty_print(
            logger, f"No existing container {container_name} running.")
    return True, "success"

def stop_db_container(deployment_id, branch, log_file_path=None):
    """
    stops db container for a specific IRIS branch.
    """
    if not log_file_path:
        log_file_path = f"{settings.STAGING_CONF['PATH_TO_HOME_DIR']}/logs/IRIS-NITK/IRIS/{branch}/{branch}.txt"
    logger = initiate_logger(log_file_path)
    db_container_name = get_db_container_name(settings.STAGING_CONF['PREFIX'], deployment_id)
    status, err = stop_containers(
        container_name=db_container_name, logger=logger)
    logger.close()
    return status, err

def delete_instance(instance, stop_db=False, remove_branch_dir=True):
    """
    Deletes the instance
    """
    container_name = instance.app_container_name
    # stop container
    clean_up(
        org_name=instance.organisation,
        repo_name=instance.repo_name,
        branch=instance.branch,
        deployment_id=instance.deployment_id,
        branch_name=instance.branch,
        remove_container=container_name,
        remove_branch_dir=remove_branch_dir,
        remove_nginx_conf=True,
        log_file_path=instance.log_file_path,
        branch_deploy_path=instance.branch_deploy_path
    )
    if stop_db:
        stop_db_container(instance.deployment_id, instance.branch, log_file_path=instance.log_file_path)
    clean_logs(org_name=instance.organisation,
                repo_name=instance.repo_name,
                branch_name=instance.branch, 
                log_file_path=instance.log_file_path)
    # delete the object from database
    instance.delete()
    return True

@shared_task(bind=True)

def deploy(self,
           url,
           user_name,
           org_name,
           repo_name,
           vcs,
           branch,
        #    external_port,
           deployment_id,
           internal_port=80,
           access_token=None,
           docker_app=None,
           docker_db=None,
           post_deploy_scripts=None,
           pre_deploy_scripts=None,
           log_file_path=None,
           clone_path=None,
           file_writes=None
           ):
    """
    Pulls changes, builds/pulls docker image, starts container, configure NGINX
    """
    # logfile where logs for this deployment are stored
    if not log_file_path:
        log_file = f"{settings.STAGING_CONF['PATH_TO_HOME_DIR']}/logs/{org_name}/{repo_name}/{branch}/{branch}.txt"
    else: 
        log_file = f"{log_file_path}/{branch}/{branch}.txt"
    logger = initiate_logger(log_file)

    # closing existing container if it exists.
    app_container_name = docker_app.get(
        'container_name', 
        str(get_app_container_name(settings.STAGING_CONF['PREFIX'], deployment_id)))
    stop_containers(container_name=app_container_name, logger=logger)
    logger.close()

    # Pull changes from git based vcs
    result, logs = pull_git_changes(
        url=url,
        user_name=user_name,
        org_name=org_name,
        repo_name=repo_name,
        branch_name=branch,
        token=access_token,
        log_file_path=log_file_path,
        clone_path=clone_path
    )

    if not result:
        print(f"git pull failed\n{logs}")

    logger = initiate_logger(log_file)

    # Building docker image
    docker_image = docker_app.get('image', None)
    if not clone_path:
        cwd = f"{settings.STAGING_CONF['PATH_TO_HOME_DIR']}/{org_name}/{repo_name}/{branch}/{repo_name}/"
    else:
        cwd = f"{clone_path}/{branch}/{repo_name}"
    if not docker_image:
        pretty_print(logger, "No Docker image provided")
        pretty_print(logger, f"Building image with {docker_app.get('dockerfile_path', 'Dockerfile')} ...")

        # building docker image and tagging it
        docker_image = app_container_name.lower()
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
    network_name=docker_app.get('network', settings.STAGING_CONF['DEPLOYMENT_DOCKER_NETWORK'])
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
                                                  str(get_db_container_name(settings.STAGING_CONF['PREFIX'], deployment_id)))

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

    if file_writes:
        for file_write in file_writes:
            pretty_print(logger, f"Writing {file_write.get('content', None)} to {file_write.get('file_path', None)}")
            status, err = write_file(
                file_path=file_write.get("file_path", None),
                content=file_write.get("content", None)
            )
            if not status:
                pretty_print(logger, err)
                return False, err
        
        pretty_print(logger, "File writes successfull")

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
