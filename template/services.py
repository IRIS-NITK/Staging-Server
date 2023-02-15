import os, datetime, requests

from subprocess import PIPE, run

from celery import shared_task

from dotenv import load_dotenv

from main.tasks.services import pull_git_changes, start_container

load_dotenv()

PREFIX = os.getenv("PREFIX", "dev")
PATH_TO_HOME_DIR = os.getenv("PATH_TO_HOME_DIR")
NGINX_ADD_CONFIG_SCRIPT = os.getenv("NGINX_ADD_CONFIG_SCRIPT_PATH")
NGINX_REMOVE_CONFIG_SCRIPT = os.getenv("NGINX_REMOVE_SCRIPT")

def pretty_print(file, text):    
    file.write(f"{datetime.datetime.now()} : {text}\n")

@shared_task(bind = True)
def deploy(self, url, repo_name, user_name, vcs, branch, external_port, internal_port = 80, access_token = None, docker_image = None, docker_network = None, dockerfile_path = None, docker_volumes = {}, docker_env_variables = {}):
    """
    Pulls changes, builds/pulls docker image, starts container, configure NGINX
    """

    # logfile where logs for this deployment are stored 
    log_file = f"{PATH_TO_HOME_DIR}/{user_name}/{repo_name}/{branch}/{branch}.txt"
    
    # Pull changes from git based vcs
    result, logs = pull_git_changes(
        url = url, 
        user_name = user_name, 
        social = vcs, 
        token = access_token, 
        org_name = user_name, 
        repo_name = repo_name, 
        branch_name = branch
    )

    if not result:
        return False, logs 

    logger = open(log_file, 'a')

    if docker_image:
        # TODO : deal with docker images in templates 
        pass 
    else:
        # no docker image, build it from dockerfile 
        if not dockerfile_path:
            # no dockerfile path 
            pretty_print(logger, "Dockerfile not provided")
            logger.close()
            return False, "Dockerfile not provided"
        
        pretty_print(logger, f"No Docker image provided") 
        pretty_print(logger, f"Building image from {dockerfile_path} ...")

        # building docker image and tagging it
        docker_image = f"{user_name.lower()}_{repo_name.lower()}:{branch.lower()}"
        result = run(
            ['docker', 'build', '--tag', docker_image, "."],
            stdout = PIPE, 
            stderr = PIPE,
            cwd = f"{PATH_TO_HOME_DIR}/{user_name}/{repo_name}/{branch}/{repo_name}/{dockerfile_path}"
        ) 

        if result.returncode !=0:
            pretty_print(logger, f"Error while building docker image from {dockerfile_path}")
            pretty_print(logger, f"ERROR : {result.stderr.decode('utf-8')}")
            logger.close()
            return False , "Could not build docker image"
        else:
            pretty_print(logger, f"Docker image built and tagged : {docker_image}")
        
        # check if this container is already running
        container_name = f"{PREFIX}_{user_name}_{repo_name}_{branch}"
        existing_container = run(
            ["docker", "container", "inspect", container_name], 
            stderr = PIPE, 
            stdout = PIPE 
        )

        if existing_container.returncode == 0:
            # container is already running, stop and remove it
            pretty_print(logger, f"Container -> {container_name} already exists, removing it ...")
            result = run(
                ["docker", "rm", "-f", container_name],
                stdout = PIPE,
                stderr = PIPE
            )
            if result.returncode !=0:
                pretty_print(logger, f"Failed to stop container")
                logger.close()
                return False, "Failed to stop container"
            pretty_print(logger, f"Removed exisiting container")
        
        pretty_print(logger, f"Starting container -> {container_name}")
        
        # start the container
        result, logs = start_container(
            container_name = container_name,
            org_name = user_name,
            repo_name = repo_name,
            branch_name = branch,
            docker_image = docker_image,
            external_port = external_port,
            internal_port = internal_port,
            volumes = docker_volumes,
            env_variables = docker_env_variables,
            docker_network = docker_network,
        )

        if not result:
            pretty_print(logger, " ⚠️ Error while starting container")
            pretty_print(logger, logs)
            logger.close()
            return False, logs
        

        # Configure NGINX 
        nginx = run(
            ["sudo", "bash", NGINX_ADD_CONFIG_SCRIPT, str(user_name.lower()), str(repo_name.lower()), str(branch.lower()), str(external_port)],
            stderr = PIPE, 
            stdout = PIPE 
        )


        if nginx.returncode != 0:
            # NGINX config failed
            pretty_print(logger, "Failed to setup NGINX config")
            pretty_print(logger, f"ERROR : {nginx.stderr.decode('utf-8')}")
            logger.close()
            return False, nginx.stderr.decode('utf-8')
  
        pretty_print(logger, f"NGINX entry done")
        pretty_print(logger, f"Successully deployed 🥳")
        pretty_print(logger, f"Visit it on : staging-{user_name.lower()}-{repo_name.lower()}-{branch.lower()}.iris.nitk.ac.in")
        
        return True, logs # log will be container id 

def health_check(url, auth_header):
    """
    Checking uptime status of site, uses auth header 
    """
    try:
        response = requests.get(url, headers={"Authorization": auth_header})
        if response.status_code == 200:
            return True
        else:
            return False
    except Exception as e:
        return False