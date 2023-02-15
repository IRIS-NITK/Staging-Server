from dotenv import load_dotenv 
import os, datetime, shutil, requests, socket
from subprocess import run, PIPE
from contextlib import closing

load_dotenv()
# environment variables are now loaded

PREFIX = os.getenv("PREFIX", "iris")
PATH_TO_HOME_DIR = os.getenv("PATH_TO_HOME_DIR")
NGINX_ADD_CONFIG_SCRIPT_IRIS = os.getenv("NGINX_ADD_CONFIG_SCRIPT_IRIS_PATH")
NGINX_REMOVE_CONFIG_SCRIPT = os.getenv("NGINX_REMOVE_SCRIPT")
DOCKER_IMAGE = os.getenv("BASE_IMAGE")
DOCKER_DB_IMAGE = os.getenv("DOCKER_DB_IMAGE","mysql:5.7")
IRIS_DOCKER_NETWORK = os.getenv("IRIS_DOCKER_NETWORK", "IRIS")
DOMAIN_PREFIX = os.getenv("DOMAIN_PREFIX", "staging")
DOMAIN = os.getenv("DOMAIN", "iris.nitk.ac.in")
DEFAULT_NETWORK = os.getenv("DEFAULT_NETWORK", "IRIS")


def find_free_port():
    """
    Finds a free port on the host machine
    """
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]
    
def health_check(url, auth_header):
    """
    Checking uptime status of site, uses auth header 
    """
    try:
        if auth_header:
            response = requests.get(url, headers={"Authorization": auth_header})
        else:
            response = requests.get(url)
        if response.status_code == 200:
            return True
        else:
            return False
    except Exception as e:
        return False
    
def pretty_print(file, text):    
    """
    Printing to log file with timestamp
    """
    file.write(f"{datetime.datetime.now()} : {text}\n")

def pull_git_changes(url, user_name, vcs, repo_name, branch_name, token = None):
    """
    Pulls the latest changes from the git repo, if the repo is not present, then it clones the repo
    """
    assert vcs.lower() in ["github", "iris.git", "gitlab"], "VCS not supported"

    log_file_path = f"{PATH_TO_HOME_DIR}/{user_name}/{repo_name}/{branch_name}/{branch_name}.txt"

    # Check if the organization/user directory exists
    if not os.path.exists(f"{PATH_TO_HOME_DIR}/{user_name}"):
        os.mkdir(f"{PATH_TO_HOME_DIR}/{user_name}")
    
    # Check if the repo directory exists
    if not os.path.exists(f"{PATH_TO_HOME_DIR}/{user_name}/{repo_name}"):
        os.mkdir(f"{PATH_TO_HOME_DIR}/{user_name}/{repo_name}")
    
    # Check if DEFAULT_BRANCH directory exists
    if not os.path.exists(f"{PATH_TO_HOME_DIR}/{user_name}/{repo_name}/DEFAULT_BRANCH"):
        os.mkdir(f"{PATH_TO_HOME_DIR}/{user_name}/{repo_name}/DEFAULT_BRANCH")
        
        # TODO : Use Python Git API instead of subprocess, with access token
        result = run(
            ["git", "clone", f"{url}", f"{PATH_TO_HOME_DIR}/{user_name}/{repo_name}/DEFAULT_BRANCH"],
            stdout = PIPE,
            stderr = PIPE,
        )

        if result.returncode != 0:
            return False, result.stderr.decode("utf-8")
        
    # Check if the branch directory exists
    if not os.path.exists(f"{PATH_TO_HOME_DIR}/{user_name}/{repo_name}/{branch_name}"):
        os.mkdir(f"{PATH_TO_HOME_DIR}/{user_name}/{repo_name}/{branch_name}")
        
        # open log file
        logger = open(log_file_path, "w")
        # copy the contents of DEFAULT_BRANCH to the branch directory
        result = run(
            ["cp", "-r", f"{PATH_TO_HOME_DIR}/{user_name}/{repo_name}/DEFAULT_BRANCH/.", f"{PATH_TO_HOME_DIR}/{user_name}/{repo_name}/{branch_name}/{repo_name}"],
            stdout = PIPE,
            stderr = PIPE,
        )
        pretty_print(logger, f"{branch_name} does not exist locally, creating a new branch")
        
        if result.returncode != 0:
            logger.close()
            return False, result.stderr.decode("utf-8")
        
        # git checkout
        result = run(
            ["git", "checkout", f"{branch_name}"],
            stdout = PIPE,
            stderr = PIPE,
            cwd = f"{PATH_TO_HOME_DIR}/{user_name}/{repo_name}/{branch_name}/{repo_name}"
        )
        
        if result.returncode != 0:
            logger.close()
            return False, result.stderr.decode("utf-8")
        
        pretty_print(logger, f"Pulled {branch_name} locally")
        
    else:
        # open log file
        logger = open(log_file_path, "a")
        pretty_print(logger, f"Pulled latest changes from {branch_name}")
        
        # git pull
        result = run(
            ["git", "pull"],
            stdout = PIPE,
            stderr = PIPE,
            cwd = f"{PATH_TO_HOME_DIR}/{user_name}/{repo_name}/{branch_name}/{repo_name}"
        )
        
        if result.returncode != 0:
            logger.close()
            return False, result.stderr.decode("utf-8")
        
        pretty_print(logger, f"Pulled latest changes from {branch_name}")
        
    return True, f"Deployed {user_name}/{repo_name}/{branch_name}"


def start_container(image_name, user_name, repo_name, branch_name, container_name, external_port, internal_port, volumes = {}, enviroment_variables = {}, docker_network = DEFAULT_NETWORK):
    """
    Generalised function to start a container for any service
    """

    command = ["docker", "run", "-d"]

    # TODO : Add support for multiple ports to be exposed
    # assert len(external_port) == len(internal_port), "Number of external ports and internal ports should be equal"

    # for ext_port, int_port in zip(external_port, internal_port):
    #     command.extend(["-p", f"{ext_port}:{int_port}"])

    command.extend(["-p", f"{external_port}:{internal_port}"])
    for src, dest in volumes.items():
        command.extend(["-v", f"{src}:{dest}"])
    for k, v in enviroment_variables.items():
        command.extend(["--env", f"{k}={v}"])
    if container_name:
        command.extend(["--name", container_name])
    if docker_network:
        command.extend(["--network", docker_network])

    command.extend([image_name])

    result = run(
        command,
        stdout = PIPE,
        stderr = PIPE
    )

    if result.returncode != 0:
        return False, result.stderr.decode("utf-8")
    return True, result.stdout.decode("utf-8")

def clean_up(org_name, repo_name, remove_container = False, remove_volume = False, remove_network = False, remove_image = False, remove_branch_dir = False, remove_all_dir = False, remove_user_dir = False):
    """
    Remove all the containers, volumes, networks and images related to the branch
    """
    
    if remove_container:
        res = run(["docker","rm","-f",remove_container],stdout=PIPE,stderr=PIPE)
        if res.returncode != 0:
            return False, res.stderr.decode('utf-8')
        res = run(["sudo","bash",NGINX_REMOVE_CONFIG_SCRIPT,org_name,repo_name,remove_branch_dir],stdout=PIPE,stderr=PIPE)
    
    if remove_volume:
        res = run(["docker","volume","rm",remove_volume],stdout=PIPE,stderr=PIPE)
        if res.returncode != 0:
            return False, res.stderr.decode('utf-8')

    if remove_network:
        res = run(["docker","network","rm",remove_network],stdout=PIPE,stderr=PIPE)
        if res.returncode != 0:
            return False, res.stderr.decode('utf-8')
    
    if remove_image:
        res = run(["docker","image","rm",remove_image],stdout=PIPE,stderr=PIPE)
        if res.returncode != 0:
            return False, res.stderr.decode('utf-8')

    if remove_branch_dir:
        try:
            absolute_path = f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{remove_branch_dir}"
            shutil.rmtree(absolute_path)
        except Exception as e:
            return False, f"Error in removing branch directory : {remove_branch_dir}\n" + str(e)
        
    if remove_all_dir:
        try:
            absolute_path = f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}"
            shutil.rmtree(absolute_path)
        except Exception as e:
            return False, f"Error in removing all directories : {remove_all_dir}\n" + str(e)
    
    if remove_user_dir:
        try:
            absolute_path = f"{PATH_TO_HOME_DIR}/{org_name}"
            shutil.rmtree(absolute_path)
        except Exception as e:
            return False, f"Error in removing user directory : {remove_user_dir}\n" + str(e)
 
    return True, "Clean up complete"

