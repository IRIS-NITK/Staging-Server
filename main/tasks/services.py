"""
Folder structure 
.
└── PATH_TO_HOME_DIR
    ├── IRIS
    │   └── IRIS
    │       ├── branch1
    │       │   └── IRIS
    │       ├── branch2
    │       │   └── IRIS
    │       └── main
    │           └── IRIS
    ├── org1
    │   └── project1
    │       ├── branch1
    │       ├── branch2
    │       └── DEFAULT_BRANCH
    ├── org2
    └── usr1

All functions return a tuple (success, message), the message is either the container id or the error message/logs 
"""
from subprocess import PIPE, run
import os, subprocess 
from celery import shared_task
from main.models import RunningInstance
# from app.getport import find_free_port
from allauth.socialaccount.models import SocialToken
import shutil
from dotenv import load_dotenv
from main.tasks.findfreeport import find_free_port
import re
import datetime 

load_dotenv()
# from ..setup import PATH_TO_HOME_DIR
PATH_TO_HOME_DIR = os.getenv("PATH_TO_HOME_DIR")
DEFAULT_BRANCH = "master" # should be a config ideally
NGINX_ADD_CONFIG_SCRIPT = os.getenv("NGINX_ADD_CONFIG_SCRIPT_PATH")
NGINX_REMOVE_CONFIG_SCRIPT = os.getenv("NGINX_REMOVE_SCRIPT")
NGINX_ADD_CONFIG_SCRIPT_IRIS = os.getenv("NGINX_ADD_CONFIG_SCRIPT_IRIS")

def write_to_log(file, text):
    file.write(f'{datetime.datetime.now()} : {text}\n')

def pull_git_changes(url, user_name,social,token = None, org_name = None, repo_name = None,branch_name = DEFAULT_BRANCH):
    """
    Pulls the latest changes from the git repo, if the repo is not present, then it clones the repo
    """
    if not (org_name and repo_name):
        return False, "Org name and repo name are required\n"

    log_file = f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/{branch_name}.txt"

    # Check if the repo is already present
    # Check if repository exists
    if os.path.exists(f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}"):       
        # Repository exists , check if branch exists
        if os.path.exists(f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}"):
            # Branch exists , pull latest changes
            logs = open(log_file,"a")
            write_to_log(logs, f"Pulling latest changes from branch {branch_name}")

            res = run(
                ['git', 'pull'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd = f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/{repo_name}"
            )

            if res.returncode != 0:
                write_to_log(logs, f"Error while pulling latest changes from branch {branch_name}")
                write_to_log(logs, res.stderr.decode('utf-8'))
                logs.close()
                return False, res.stderr.decode('utf-8')
            write_to_log(logs, f"Successfully pulled latest changes from branch {branch_name}")
            write_to_log(logs, res.stdout.decode('utf-8'))
            logs.close()
            return True, res.stdout.decode('utf-8')

        else:
            # Branch does not exist , could be a new branch  
            # Pull latest changes from default branch
            res = run(
                ['git', 'checkout', branch_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/DEFAULT_BRANCH/{repo_name}"
            )

            if res.returncode != 0:
                return False, res.stderr.decode('utf-8')
                
            res = run(
                ['git', 'pull'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/DEFAULT_BRANCH/{repo_name}"
            )

            if res.returncode != 0:
                return False, res.stderr.decode('utf-8')

            os.makedirs(f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}")
            logs = open(log_file,"w")
            write_to_log(logs, f"Branch {branch_name} does not exist locally, pulling it")
            
            # copy latest changes to branch direcotry
            res = subprocess.run(
                ['cp', '-r', f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/DEFAULT_BRANCH/{repo_name}/.", f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/{repo_name}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd = f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/DEFAULT_BRANCH/{repo_name}"
            )

            if res.returncode != 0:
                write_to_log(logs, f"Error while copying files from {DEFAULT_BRANCH} to {branch_name}")
                write_to_log(logs, res.stderr.decode('utf-8'))
                logs.close()
                return False, res.stderr.decode('utf-8')
            
            write_to_log(logs, f"Successfully pulled branch {branch_name} locally")
            logs.close()
            return True, res.stdout.decode('utf-8')
    # Repository does not exist , clone it
    else:
        temp_logging_text = ""
        if not os.path.exists(f"{PATH_TO_HOME_DIR}/{org_name}"):
            temp_logging_text = f'\n{datetime.datetime.now()} : Organization {org_name} does not exist locally, creating it\n'
            os.makedirs(f"{PATH_TO_HOME_DIR}/{org_name}")

        # org exists , repo does not exist , could be a new repo , so clone it
        os.makedirs(f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/DEFAULT_BRANCH")
        temp_logging_text += f'\n{datetime.datetime.now()} : Repository {repo_name} does not exist locally, creating it\n'

        # repo_url = "https://oauth2:"+token+"@github.com/"+user_name+"/"+repo_name+".git"
        if token and social.lower() == "github":
            v1,v2 = get_org_and_repo_name_v2(url,'github')
            url = f'https://{user_name}:{token}@github.com/{v1}/{v2}'
        else:
            url = f'ssh://git@git.iris.nitk.ac.in:5022/{org_name}/{repo_name}.git'

        parent_dir = f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/DEFAULT_BRANCH"
        local_dir = os.path.join(parent_dir, repo_name)

        res = run(
            ['git', 'clone', url , local_dir],
            stdout=PIPE,
            stderr=PIPE,
        )

        temp_logging_text += f'\n{datetime.datetime.now()} : Repository {repo_name} does not exist locally, cloning it\n'
        if res.returncode != 0:
            return False, res.stderr.decode('utf-8')

        os.makedirs(f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}")
        try:
            logs = open(log_file,"a")
        except:
            logs = open(log_file,"w")
        logs.write(temp_logging_text)
        write_to_log(logs, f"Branch {branch_name} does not exist locally, creating it")
        
        # copy latest changes to branch direcotry
        res = run(
            ['git', 'checkout', branch_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd = f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/DEFAULT_BRANCH/{repo_name}"
        )
        if res.returncode != 0:
            write_to_log(logs, f"Error while creating branch {branch_name}")
            write_to_log(logs, res.stderr.decode('utf-8'))
            return False, res.stderr.decode('utf-8')
        
        write_to_log(logs, f"Successfully pulled latest changes from {branch_name} branch")
       
        # copy latest changes to branch direcotry
        res = run(
            ['cp', '-r', f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/DEFAULT_BRANCH/{repo_name}/.", f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/{repo_name}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd = f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/DEFAULT_BRANCH/{repo_name}"
        )

        if res.returncode != 0:
            write_to_log(logs, f"Error while copying files from {DEFAULT_BRANCH} to {branch_name}")
            write_to_log(logs, res.stderr.decode('utf-8'))
            return False, res.stderr.decode('utf-8')
        write_to_log(logs, f"Successfully copied changes to branch {branch_name} locally")
        
        return True, res.stdout.decode('utf-8') 



def start_db_container(db_image, db_name, db_dump_path, volume_name, volume_bind_path, db_env_variables, network_name):
    command = ["docker", "run"] 
    if db_name:
        command.extend(["--name", db_name])
    if db_dump_path:
        command.extend(["-v", f"{db_dump_path}:/docker-entrypoint-initdb.d/"])
    if volume_name and volume_bind_path:
        command.extend(["-v", f"{volume_name}:{volume_bind_path}"])
    if db_env_variables:
        command.extend([*db_env_variables])
    if network_name:
        command.extend(["--network", network_name])
    command.extend(["--detach", "--rm", db_image])

    res = run(
        command,
        stdout=PIPE,
        stderr=PIPE,
    )    
    if res.returncode != 0:
        print(res.stderr.decode('utf-8'))
        return False, res.stderr.decode('utf-8')
    return True, res.stdout.decode('utf-8')


def start_container(container_name, org_name, repo_name, branch_name, docker_image, external_port, internal_port = 3000, docker_network = "IRIS", volumes = {}, env_variables = {}):
    """
    Generalised function to start a container for any service
    """
    command = ["docker", "run"]
    command.extend(["-d", "-p", f"{external_port}:{internal_port}"])
    for src, dest in volumes.items():
        command.extend(["-v", f"{src}:{dest}"])
    for k, v in env_variables.items():
        command.extend(["--env", f"{k}={v}"])
    if container_name:
        command.extend(["--name", container_name])
    if docker_network:
        command.extend(["--network", docker_network])
    command.extend(["--detach"]) 
    # command.extend(["--rm"]) # uncomment this to remove container after it stops

    command.extend([docker_image])

    res = run(
        command,
        stdout=PIPE,
        stderr=PIPE,
        cwd=f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}"
    )
    running_instance = RunningInstance.objects.get(branch=branch_name,repo_name=repo_name,organisation=org_name)
    if res.returncode != 0:
        running_instance.status = RunningInstance.STATUS_ERROR
        print(res.stderr.decode('utf-8'))
        return False, res.stderr.decode('utf-8')
    else:
        running_instance.status = RunningInstance.STATUS_SUCCESS
    running_instance.save()
    return True, res.stdout.decode('utf-8') 

def create_network(network_name):
    res = run(
        ["docker", "network", "create", network_name],
        stdout=PIPE,
        stderr=PIPE,
    )
    if res.returncode != 0:
        return False, res.stderr.decode('utf-8')
    return True, res.stdout.decode('utf-8')

def attach_container_to_network(container_id, network_name):
    """
    Attach a container to a network, can use either container name or container id
    """
    res = run(
        ["docker", "network", "connect", network_name, container_id],
        stdout=PIPE,
        stderr=PIPE,
    )
    if res.returncode != 0:
        return False, res.stderr.decode('utf-8')
    return True, res.stdout.decode('utf-8')

def stop_container(branch_name, repo_name, org_name):
    yield "Stopping the app\n"
    prefix = "iris"
    container_name = f"{prefix}_{org_name}_{repo_name}_{branch_name}"
    res = run(["docker","rm","-f",container_name],stdout=PIPE,stderr=PIPE)
    yield "Removing Old Logs\n"
    file_path = f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{DEFAULT_BRANCH}/{branch_name}"+".txt"
    res = run(["rm",file_path])
    yield "Removing Nginx Script\n"
    res = run(["sudo","bash",NGINX_REMOVE_CONFIG_SCRIPT,org_name,repo_name,branch_name],stdout=PIPE,stderr=PIPE)
    if res.returncode == 0:
        yield res.stdout.decode('utf-8')
    else:
        yield res.stderr.decode('utf-8')

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

@shared_task(bind=True)
def deploy_from_git_template(self, url, user_name,token = None, social = None, org_name = None, repo_name = None, branch_name = DEFAULT_BRANCH, internal_port = 80, external_port = 3000, docker_image = None, dockerfile_path = None, docker_volumes = {}, docker_env_variables = {}, default_branch = "main", docker_network = None):
    
    log_file = f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/{branch_name}.txt"

    temp_org_name, temp_repo_name = get_org_and_repo_name_v2(url=url)
    if not org_name:
        org_name = temp_org_name
    if not repo_name:
        repo_name = temp_repo_name

    # pull git repo
    res, msg = pull_git_changes(
        url=url,
        user_name=user_name,
        social=social,
        token=token,
        org_name=org_name,
        repo_name=repo_name,
        branch_name=branch_name,
    )
    if not res:
        return False, msg
    
    logs = open(log_file,'a')
    
    if docker_image != None:
        write_to_log(logs, f"Searching for Docker image : {docker_image}")
        res = run(
            ['docker', 'inspect', docker_image],
            stdout=PIPE,
            stderr=PIPE
        )
        if res.returncode != 0:
            write_to_log(logs, f"{docker_image} not found")
            docker_image = None
        else:
            write_to_log(logs, f"{docker_image} found")

    if docker_image == None:
        if dockerfile_path == None:
            write_to_log(logs, "Dockerfile not provided")
            logs.close()
            return False, "Dockerfile not provided"
        docker_image = f"{org_name.lower()}_{repo_name.lower()}_{branch_name.lower()}"
        write_to_log(logs, f"Docker image not provided, building image")
        print(docker_image)
        res = run(
            ['docker', 'build', '--tag', docker_image, "."],
            stdout=PIPE,
            stderr=PIPE,
            cwd=f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/{repo_name}/"
        )
        if res.returncode != 0:
            write_to_log(logs, f"Error while building docker image")
            write_to_log(logs, res.stderr.decode('utf-8'))
            logs.close()
            return False, "Error while building docker image\n" + res.stderr.decode('utf-8')
        else:
            write_to_log(logs, f"Docker image {docker_image} built successfully")
            logs.write(f"{datetime.datetime.now()} : Docker image built successfully\n\t\t\ttagged : {docker_image}\n")
    
    write_to_log(logs, f"Starting container from image : {docker_image}")
    prefix = "iris"
    container_name = f"{prefix}_{org_name}_{repo_name}_{branch_name}"
    check_container_exists = run(["docker","container","inspect",container_name],stdout=PIPE,stderr=PIPE)

    if check_container_exists.returncode == 0:
        write_to_log(logs, f"Container already exists : {container_name}")
        write_to_log(logs, f"Removing existing container : {container_name}")
        res = run(
            ["docker","rm","-f",container_name],
            stdout=PIPE,
            stderr=PIPE
        )
        if res.returncode != 0:
            write_to_log(logs, f"Error while removing existing container : {container_name}")
            logs.close()
            return False, "Error while removing existing container\n" + res.stderr.decode('utf-8')
        write_to_log(logs, f"Existing container removed : {container_name}")

    write_to_log(logs, f"Starting container : {container_name}")    
    res, container_id = start_container(
        container_name=container_name,
        org_name=org_name,
        repo_name=repo_name,
        branch_name=branch_name,
        docker_image=docker_image,
        external_port=external_port,
        internal_port=internal_port,
        volumes=docker_volumes,
        env_variables=docker_env_variables,
        docker_network=docker_network,
    )

    if not res:
        write_to_log(logs, f"Error while starting container : {container_name}")
        write_to_log(logs, container_id)
        logs.close()
        return False, container_id

    # link : staging-<org_name>-<repo_name>-<branch_name>.iris.nitk.ac.in 
    res = run(
            ["sudo", "bash", NGINX_ADD_CONFIG_SCRIPT, str(org_name.lower()) , str(repo_name.lower()), str(branch_name.lower()), str(external_port), ],
            stdout=PIPE,
            stderr=PIPE,
        )
    if res.returncode != 0:
        logs.write(f"{datetime.datetime.now()} : Error while adding nginx config\n")
        logs.close()
        return False, "Error while adding nginx config\n" + res.stderr.decode('utf-8')
    logs.write(f"{datetime.datetime.now()} : Nginx config added successfully\n")
    logs.write(f"\n{datetime.datetime.now()} : 🥳 Container started successfully \n\ncontainer name : {container_name}\ncontainer id : {container_id}\n")
    logs.write(f"Visit it on : staging-{org_name.lower()}-{repo_name.lower()}-{branch_name.lower()}.iris.nitk.ac.in\n\n")
    return True, container_id


@shared_task(bind=True)
def deploy_from_git(self, token, url, social, user_name,org_name, repo_name, branch_name, internal_port = 3000,  external_port = None, src_code_dir = None , dest_code_dir = None, docker_image=None, volumes = {}, DEFAULT_BRANCH = "master"):
    
    # pull git repo
    org_name,repo_name = get_org_and_repo_name_v2(url,'iris_git')

    log_file = f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/{branch_name}.txt"

    res, msg = pull_git_changes(
        url=url,
        user_name=user_name,
        social=social,
        token=token,
        org_name=org_name,
        repo_name=repo_name,
        branch_name=branch_name,
    )        
    logs = open(log_file,'a')
    image_name = ""
    docker_image = ""
    db_name = "db"
    if url == 'https://git.iris.nitk.ac.in/IRIS-NITK/IRIS.git' or url=="ssh://git@git.iris.nitk.ac.in:5022/IRIS-NITK/IRIS.git":
        #docker_image = "git-registry.iris.nitk.ac.in/iris-teams/systems-team/staging-server/dev-iris:latest"
        docker_image = os.getenv("BASE_IMAGE")
    else:
        docker_image = f"{org_name.lower()}_{repo_name.lower()}_{branch_name.lower()}"
        db_name = f"{org_name.lower()}_{repo_name.lower()}_db"
    # start container 
    db_image = "mysql:5.7"
    env_var_args = {
                "MYSQL_ROOT_PASSWORD": "root",
                "MYSQL_DATABASE": "dev",
                "MYSQL_USER": "dev123",
                "MYSQL_PASSWORD": "dev123",
    }

    db_env_variables = []

    for key, value in env_var_args.items():
        db_env_variables.extend(["--env", f"{key}={value}"])
    try:
        f = open(log_file,'a')
    except FileNotFoundError:
        f = open(log_file,'w')
    check_db_container_exists = run(["docker","container","inspect",db_name],stdout=PIPE,stderr=PIPE)
    if check_db_container_exists.returncode != 0:
        f.write("Starting Database Container"+"\n")
        res, msg = start_db_container(db_image, db_name, None, None, None, db_env_variables, "IRIS")
        f.write(msg+"\n")
    else: 
        f.write("Database Container "+ db_name + " already exists."+"\n")


    #check_image_exists = run(["docker","image","inspect",docker_image],stdout=PIPE,stderr=PIPE)

    write_to_log(logs, f"Building docker image:")
    res = run(
        ['docker', 'build', '--tag', docker_image, "."],
        stdout=PIPE,
        stderr=PIPE,
        cwd=f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/{repo_name}/"
    )
    if res.returncode != 0:
        write_to_log(logs, f"Error while building docker image")
        write_to_log(logs, res.stderr.decode('utf-8'))
        logs.close()
        return False, "Error while building docker image\n" + res.stderr.decode('utf-8')
    else:
        write_to_log(logs, f"Docker image {docker_image} built successfully")
        logs.write(f"{datetime.datetime.now()} : Docker image built successfully\n\t\t\ttagged : {docker_image}\n")
    
    # # org_name, repo_name, branch_name, docker_image, external_port, internal_port = 80, src_code_dir = None, dest_code_dir = None
    env_variables = {}

    if repo_name == "IRIS":
        src = f'{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/{repo_name}/' + "config/initializers"
        res = run([
            "cp",f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/{repo_name}/config/initializers/nitk_setting.rb.example",
            f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/{repo_name}/config/initializers/nitk_setting.rb"
        ])
        res = run([
            "cp",f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/session_store.rb",
            f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/{repo_name}/config/initializers/session_store.rb"
        ])
        res = run([
            "cp",f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/{repo_name}/config/initializers/nitk_setting.rb.example",
            f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/{repo_name}/config/initializers/secret_token.rb"
        ])
        src = f'{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/{repo_name}/'
        dest = "/iris-data/" 
        volumes = {
             src : dest,
        }
        env_variables = {
            "RAILS_ENV": "development"
        }
    
    write_to_log(logs, f"Starting container from image : {docker_image}")
    prefix = "iris"
    container_name = f"{prefix}_{org_name.lower()}_{repo_name.lower()}_{branch_name.lower()}"
    check_container_exists = run(["docker","container","inspect",container_name],stdout=PIPE,stderr=PIPE)

    if check_container_exists.returncode == 0:
        write_to_log(logs, f"Container already exists : {container_name}")
        write_to_log(logs, f"Removing existing container : {container_name}")
        res = run(
            ["docker","rm","-f",container_name],
            stdout=PIPE,
            stderr=PIPE
        )
        if res.returncode != 0:
            write_to_log(logs, f"Error while removing existing container : {container_name}")
            logs.close()
            return False, "Error while removing existing container\n" + res.stderr.decode('utf-8')
        write_to_log(logs, f"Existing container removed : {container_name}")

    write_to_log(logs, f"Starting container : {container_name}")    

    res, container_id = start_container(
        container_name=container_name,
        org_name=org_name,
        repo_name=repo_name,
        branch_name=branch_name,
        docker_image=docker_image,
        external_port=external_port,
        internal_port=internal_port,
        volumes=volumes,
        env_variables=env_variables
    )

    if not res:
        write_to_log(logs, f"Error while starting container : {container_name}")
        write_to_log(logs, container_id)
        logs.close()
        return False, container_id

    #nginx config 
    res = run(
        ["sudo", "bash", NGINX_ADD_CONFIG_SCRIPT_IRIS, str(branch_name), str(external_port)],
        stdout=PIPE,
        stderr=PIPE,
    )
    if res.returncode != 0:
        logs.write(f"{datetime.datetime.now()} : Error while adding nginx config\n")
        logs.close()
        return False, "Error while adding nginx config\n" + res.stderr.decode('utf-8')
    logs.write(f"{datetime.datetime.now()} : Nginx config added successfully\n")
    logs.write(f"\n{datetime.datetime.now()} : 🥳 Container started successfully \n\ncontainer name : {container_name}\ncontainer id : {container_id}\n")
    logs.write(f"Visit it on : staging-{org_name.lower()}-{repo_name.lower()}-{branch_name.lower()}.iris.nitk.ac.in\n\n")
    return True, container_id


def get_org_and_repo_name_v2(url, social = "github"):
    if social == "github":
        github_match = re.match(r'(?:https?://)?github.com/([^/]+)/([^/]+)(?:\.git)?', url)
        if github_match:
            repo = url.rsplit("/",1)[-1].replace(".git","")
            return (github_match.group(1), repo)

    elif social == "gitlab":
        gitlab_match = re.match(r'(?:https?://)?gitlab.com/([^/]+)/([^/]+)(?:\.git)?', url)
        if gitlab_match:
            repo = url.rsplit("/",1)[-1].replace(".git","")
            return (gitlab_match.group(1), repo)
    
    elif social == "iris_git":
        iris_git_match = re.search(r'https://git\.iris\.nitk\.ac\.in/(.*)/(.*)\.git', url)
        if iris_git_match:
            org_name = iris_git_match.group(1)
            repo_name = iris_git_match.group(2)
            return (org_name, repo_name)
        return None, None

