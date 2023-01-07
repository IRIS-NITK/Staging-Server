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

load_dotenv()
# from ..setup import PATH_TO_HOME_DIR
# PATH_TO_HOME_DIR = os.getenv("PATH_TO_HOME_DIR")
DEFAULT_BRANCH = "master" # should be a config ideally
log_file = ""
NGINX_ADD_CONFIG_SCRIPT = os.getenv("NGINX_ADD_CONFIG_SCRIPT_PATH")
NGINX_REMOVE_CONFIG_SCRIPT = os.getenv("NGINX_REMOVE_SCRIPT")

PATH_TO_HOME_DIR = "/home/vinayakj02/staging_area"


def pull_git(url, token, org_name, repo_name):

    global log_file
    log_file = f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{DEFAULT_BRANCH}/{DEFAULT_BRANCH}.txt"
    
    # get name of repo
    # repo_name = url.split('/')[-1].split('.')[0]
    # main or master ? -> DEFAULT_BRANCH
    # check if org exists
    if os.path.exists(f"{PATH_TO_HOME_DIR}/{org_name}"):
        # org exists, check if repo exists
        if os.path.exists(f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}"):
            
            f = open(log_file,"a")
            f.write("Repo already exists, pulling latest changes\n")

            result = subprocess.run(
                            ['git', 'pull'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd = f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{DEFAULT_BRANCH}/{repo_name}"
            )

            if result.returncode != 0:
                return False, result.stderr.decode('utf-8')
            return True, result.stdout.decode('utf-8')
        else:
            # repo does not exist , could be a new repo , so clone it
            os.makedirs(f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{DEFAULT_BRANCH}")
            # f = open(log_file,"a")
            # f.write("Repo does not exist, cloning it for the first time\n")
            user_name = url.split('/')[3]
            repo_url = "https://oauth2:"+token+"@github.com/"+user_name+"/"+repo_name+".git"
            parent_dir = f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{DEFAULT_BRANCH}"
            local_dir = os.path.join(parent_dir, repo_name)
            res = run(
                ['git', 'clone', repo_url,local_dir],
                stdout=PIPE,
                stderr=PIPE,
            )
            f = open(log_file,'w')
            f.write("Starting deployment\n")
            f.write("Repo did not exist, cloning it for the first time\n")
            if res.returncode != 0:
                f.write("Error while cloning repo\n")
                return False, res.stderr.decode('utf-8')
            f.write("Repo cloned successfully\n")
        return True, res.stdout.decode('utf-8')
    else:
        os.makedirs(f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{DEFAULT_BRANCH}")
        f = open(log_file,"a")
        f.write("Org does not exist, cloning it for the first time\n")
        user_name = url.split('/')[3]
        repo_url = "https://oauth2:"+token+"@github.com/"+user_name+"/"+repo_name+".git"
        parent_dir = f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{DEFAULT_BRANCH}"
        local_dir = os.path.join(parent_dir, repo_name)
        res = run(
                ['git', 'clone', repo_url,local_dir],
                stdout=PIPE,
                stderr=PIPE,
            )
        if res.returncode != 0:
            return False, res.stderr.decode('utf-8')
        return True, res.stdout.decode('utf-8')


def get_git_branches(repo_name, org_name):
    f = open(log_file,"a")
    f.write("Getting branches\n")
    res = run(
        ['git', 'branch', '-a'],
        stdout=PIPE,
        stderr=PIPE,
        cwd=f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{DEFAULT_BRANCH}/{repo_name}"
    )
    if res.returncode != 0:
        return False, res.stderr.decode('utf-8')
    return True, res.stdout.decode('utf-8')

def checkout_git_branch(repo_name, org_name, branch_name):
    f = open(log_file,"a")
    f.write(f"Switching to branch : {branch_name}\n")
    res = run(
        ['git', 'checkout', branch_name],
        stdout=PIPE,
        stderr=PIPE,
        cwd=f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{DEFAULT_BRANCH}/{repo_name}"
    )
    if res.returncode != 0:
        return False, res.stderr.decode('utf-8')
    return True, res.stdout.decode('utf-8')

def start_db_container(db_image, db_name, db_dump_path, volume_name, volume_bind_path, db_env_variables, network_name):
    """
    run([
        "docker", "run",
        "--name", db_name,
        "-v", f"{db_dump_path}:/docker-entrypoint-initdb.d/",
        "-v", f"{volume_name}:{volume_bind_path}",
        "--env", *[f"{k}={v}" for k,v in db_env_variables.items()],
        "--detach",
        "--rm",
        db_image
    ])
    
    """
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
    # volume_args = []
    # for host_path, container_path in volumes.items():
    #     volume_args.append(f"{host_path}:{container_path}")

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
    res = run(["sudo","bash",NGINX_REMOVE_CONFIG_SCRIPT,branch_name],stdout=PIPE,stderr=PIPE)
    if res.returncode == 0:
        yield res.stdout.decode('utf-8')
    else:
        yield res.stderr.decode('utf-8')

def clean_up(org_name, repo_name, remove_container = False, remove_volume = False, remove_network = False, remove_image = False, remove_branch_dir = False, remove_all_dir = False, remove_user_dir = False):
    """
    Remove all the containers, volumes, networks and images related to the branch
    """
    if remove_container:
        yield f"Removing container {remove_container}\n"
        res = run(["docker","rm","-f",remove_container],stdout=PIPE,stderr=PIPE)
        if res.returncode == 0:
            yield f"Removed container : {remove_container}\n" + res.stdout.decode('utf-8') 
        else:
            yield f"Error in removing container : {remove_container}" + res.stderr.decode('utf-8')
    
    if remove_volume:
        yield f"Removing volume : {remove_volume}\n"
        res = run(["docker","volume","rm",remove_volume],stdout=PIPE,stderr=PIPE)
        if res.returncode == 0:
            yield f"Removed volume : {remove_volume}\n" + res.stdout.decode('utf-8')
        else:
            yield f"Error in removing volume : {remove_volume}" + res.stderr.decode('utf-8')

    if remove_network:
        yield f"Removing network : {remove_network}\n"
        res = run(["docker","network","rm",remove_network],stdout=PIPE,stderr=PIPE)
        if res.returncode == 0:
            yield f"Removed network : {remove_network}\n" + res.stdout.decode('utf-8')
        else:
            yield f"Error in removing network : {remove_network}" + res.stderr.decode('utf-8')
    
    if remove_image:
        yield f"Removing image : {remove_image}\n"
        res = run(["docker","image","rm",remove_image],stdout=PIPE,stderr=PIPE)
        if res.returncode == 0:
            yield f"Removed image : {remove_image}\n" + res.stdout.decode('utf-8')
        else:
            yield f"Error in removing image : {remove_image}" + res.stderr.decode('utf-8')

    if remove_branch_dir:
        yield f"Removing branch directory : {remove_branch_dir}\n"
        try:
            absolute_path = f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{remove_branch_dir}/{repo_name}"
            shutil.rmtree(absolute_path)
            yield f"Removed branch directory : {remove_branch_dir}\n"
        except Exception as e:
            yield f"Error in removing branch directory : {remove_branch_dir}\n" + str(e)
        
    if remove_all_dir:
        yield f"Removing all directories : {remove_all_dir}\n"
        try:
            absolute_path = f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}"
            shutil.rmtree(absolute_path)
            yield f"Removed all directories : {remove_all_dir}\n"
        except Exception as e:
            yield f"Error in removing all directories : {remove_all_dir}\n" + str(e)
    
    if remove_user_dir:
        yield f"Removing user directory : {remove_user_dir}\n"
        try:
            absolute_path = f"{PATH_TO_HOME_DIR}/{org_name}"
            shutil.rmtree(absolute_path)
            yield f"Removed user directory : {remove_user_dir}\n"
        except Exception as e:
            yield f"Error in removing user directory : {remove_user_dir}\n" + str(e)
    
    yield "Clean up complete\n"

@shared_task(bind=True)
def deploy_from_git_template(self, token, url, social, org_name, repo_name, branch_name, internal_port, external_port, docker_image, dockerfile_path, docker_volumes = {}, docker_env_variables = {}, default_branch = "main", docker_network = None):
    # global log_file
    # log_file = f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{default_branch}/{branch_name}.txt"
    # logfile = open(log_file,'w')
    # logfile.write("Starting deployment\n")
    # logfile.close()
    # pull git repo
    result,msg = pull_git(url,token,repo_name=repo_name, org_name=org_name)
    logfile = open(log_file,'a')
    logfile.write(msg)
    if not result:
        logfile.write("Error in pulling git repo\ndeploy_from_git_template->pull_git\n")
        logfile.close()
        return False, msg
    
    # get branches
    res, branches  = get_git_branches(repo_name, org_name)
    logfile.write(branches)
    if not res:
        logfile.write("Error in getting branches\nget_git_branches->deploy_from_git_template\n")
        logfile.close()
        return False, branches
    
    # check if branch exists
    if branch_name not in branches:
        logfile.write("Branch does not exist in git repo\n")
        logfile.close()
        return False, "Branch does not exist in git repo"
    
    # checkout branch
    res, msg = checkout_git_branch(repo_name, branch_name, org_name)
    logfile.write(msg)
    if not res:
        logfile.write("Error in checking out branch\ndeploy_from_git_template->checkout_git_branch\n")
        logfile.close()
        return False, msg
    
    # check if branch was already deployed previously
    if branch_name not in os.listdir(f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}"):
        # branch was not deployed previously
        logfile.write("Branch was not deployed previously\n")
        # create a new directory for the branch
        logfile.write(f"Creating a new directory for the branch : {PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}\n")
        os.mkdir(f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}")
        # copy the code from the default branch to the new branch
        if len(docker_volumes) == 0:
            res = run(
                ['cp', '-r', f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{DEFAULT_BRANCH}/{repo_name}/", f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/{repo_name}/"],
                stdout=PIPE,
                stderr=PIPE
            )
            if res.returncode != 0:
                logfile.write("Error while copying code from default branch to new branch\ndeploy_from_git_template->run->cp\n")
                logfile.close()
                return False, "Error while copying code from default branch to new branch\n" + res.stderr.decode('utf-8')
        else:
            for src_folder, dest_folder in docker_volumes.items():
                res = run(
                    ['cp', '-r', f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{DEFAULT_BRANCH}/{repo_name}/{src_folder}", f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/{dest_folder}"],
                    stdout=PIPE,
                    stderr=PIPE
                )
                if res.returncode != 0:
                    return False, "Error while mounting code, incorrect mapping\n" + res.stderr.decode('utf-8')
    
        
    if docker_image == None:
        
        if dockerfile_path == None:
            logfile.write("Dockerfile not provided\n")
            logfile.close()
            return False, "Dockerfile not provided"
        logfile.write(f"Docker image not provided, building image from {dockerfile_path}\n")
        docker_image = f"{org_name}/{repo_name}:{branch_name}"
        res = run(
            ['docker', 'build', '-t', docker_image, "."],
            stdout=PIPE,
            stderr=PIPE,
            cwd=f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/{repo_name}"
        )
        if res.returncode != 0:
            logfile.write("Error while building docker image\ndeploy_from_git_template->run->docker build\n")
            logfile.close()
            return False, "Error while building docker image\n" + res.stderr.decode('utf-8')
        else:
            logfile.write(f"Docker image built successfully\ntagged : {docker_image}\n")
    
    logfile.write(f"Starting container {docker_image}\n")
    

    """
    start_container(container_name, org_name, repo_name, branch_name, docker_image, external_port, internal_port = 3000, docker_network = "IRIS", volumes = {}, env_variables = {}):
    """
    
    # # org_name, repo_name, branch_name, docker_image, external_port, internal_port = 80, src_code_dir = None, dest_code_dir = None
    prefix = "iris_template"
    container_name = f"{prefix}_{org_name}_{repo_name}_{branch_name}"
    check_container_exists = run(["docker","container","inspect",container_name],stdout=PIPE,stderr=PIPE)

    
    if check_container_exists.returncode == 0:
        logfile.write(f"Container already exists : {container_name}\n")
        logfile.write(f"Removing existing container : {container_name}\n")
        res = run(
            ["docker","rm","-f",container_name],
            stdout=PIPE,
            stderr=PIPE
        )
        if res.returncode != 0:
            logfile.write("Error while removing existing container\ndeploy_from_git_template->run->docker rm\n")
            logfile.close()
            return False, "Error while removing existing container\n" + res.stderr.decode('utf-8')
        logfile.write(f"Existing container removed : {container_name}\n")
    
    logfile.write(f"Starting container : {container_name}\n")
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
        docker_network=docker_network
    )

    if not res:
        logfile.write(f"Error while starting container : {container_name}\n")
        logfile.close()
        return False, container_id
    
    logfile.write(f"Container started successfully \ncontainer name : {container_name}\ncontainer id : {container_id}\n")

    # res = run(
    #         ["sudo", "bash", NGINX_ADD_CONFIG_SCRIPT,str(branch_name), str(external_port)],
    #         stdout=PIPE,
    #         stderr=PIPE,
    #     )

@shared_task(bind=True)
def deploy_from_git(self, token, url, social, org_name, repo_name, branch_name, internal_port = 3000,  src_code_dir = None , dest_code_dir = None, docker_image=None, volumes = {}, DEFAULT_BRANCH = "main"):
    

    global log_file
    log_file = PATH_TO_HOME_DIR+"/"+org_name+"/"+repo_name+"/"+DEFAULT_BRANCH+"/"+branch_name+".txt"

    # pull git repo
    result,msg = pull_git(url,token,repo_name=repo_name, org_name=org_name)
    f = open(log_file,'a')
    f.write(msg)
    if not result:
        return False, msg 


    # get branches
    res, branches  = get_git_branches(repo_name, org_name=org_name)
    if not res:
        f = open(log_file,'a')
        f.write(branches)
        return False, branches
        
    
    # check if branch exists
    if branch_name not in branches:
        return False, "Branch does not exist in the git repository"
    
    # checkout branch
    res = checkout_git_branch(repo_name, branch_name=branch_name, org_name=org_name)
    f = open(log_file,'a')
    # f.write(res[1])
    if not res[0]:
        return False, res[1]
    
    # check if branch was already deployed previously
    if branch_name not in os.listdir(f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}"):
        # branch was not deployed previously
        # create a new directory for the branch
        os.mkdir(f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}")
        # copy the code from the default branch to the new branch
        if src_code_dir == None:
            res = run(
                ['cp', '-r', f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{DEFAULT_BRANCH}/{repo_name}/", f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/{repo_name}/"],
                stdout=PIPE,
                stderr=PIPE
            )
        else:
            if len(src_code_dir) != len(dest_code_dir):
                return False, "Error in mounting the files, incorrect mapping"
            for src_folder, dest_folder in zip(src_code_dir, dest_code_dir):
                res = run(
                    ['cp', '-r', f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{DEFAULT_BRANCH}/{repo_name}/{src_folder}", f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/{dest_folder}"],
                    stdout=PIPE,
                    stderr=PIPE
                )
                if res.returncode != 0:
                    return False, "Error while mounting code, incorrect mapping\n" + res.stderr.decode('utf-8')
    
        
    image_name = ""
    docker_image = ""
    if url == 'https://git.iris.nitk.ac.in/IRIS-NITK/IRIS.git':
        docker_image = "dev27"
    else:
        image_name = org_name+"/"+repo_name+":"+branch_name
        docker_image = image_name.lower()
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

    db_name = "db"
    f.write("Starting Database Container"+"\n")
    res, msg = start_db_container(db_image, "db", None, None, None, db_env_variables, "IRIS")
    f.write(msg+"\n")


    check_image_exists = run(["docker","image","inspect",docker_image],stdout=PIPE,stderr=PIPE)

    if check_image_exists.returncode != 0:
        res = run(
            ['docker', 'build', '-t', docker_image, "."],
            stdout=PIPE,
            stderr=PIPE,
            cwd=f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/{repo_name}"
        )
        if res.returncode != 0:
            f = open(log_file,'a')
            f.write(res.stdout.decode('utf-8')+"\n")
            return
    
    
    # # org_name, repo_name, branch_name, docker_image, external_port, internal_port = 80, src_code_dir = None, dest_code_dir = None
    prefix = "iris"
    container_name = f"{prefix}_{org_name}_{repo_name}_{branch_name}"
    check_container_exists = run(["docker","container","inspect",container_name],stdout=PIPE,stderr=PIPE)
    external_port = find_free_port()
    env_variables = {}

    if org_name == "NITK-IRIS":
        src = f'{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/{repo_name}/' + "config/initializers"
        res = run(["cp","/home/jokesta/Desktop/nitk_setting.rb",src],stdout=PIPE,stderr=PIPE)
        res = run(["cp","/home/jokesta/Desktop/secret_token.rb",src],stdout=PIPE,stderr=PIPE)
        src = f'{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/{repo_name}/'
        dest = "/iris-data/" 
        volumes = {
             src : dest,
        }
        env_variables = {
            "RAILS_ENV": "development"
        }
    f = open(log_file,'a')

    if check_container_exists.returncode !=0:
        #create container under newtork="abc"
        #create database container under network ='abc'
        f.write("Starting Container")
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
        f.write(container_id+"\n")
    else:
        f.write("Removing Exisiting Container"+container_name+"\n")
        res1 = run(
            ["docker","rm","-f",container_name],
            stdout=PIPE,
            stderr=PIPE
        )
        if res1.returncode != 0:
            f.write("\nError : \n"+res1.stderr.decode('utf-8')+"\n")
            return False, res1.stderr.decode('utf-8')

        f.write("Starting Container"+"\n")

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
        f.write(container_id+"\n")

    #nginx config 

    res = run(
            ["sudo", "bash", NGINX_ADD_CONFIG_SCRIPT,str(branch_name), str(external_port)],
            stdout=PIPE,
            stderr=PIPE,
        )

def get_repo_name(url):
    github_match = re.match(r'(?:https?://)?github.com/(.+)/(.+)', url)
    if github_match:
        return github_match.group(2)

    gitlab_match = re.match(r'(?:https?://)?gitlab.com/(.+)/(.+)', url)
    if gitlab_match:
        return gitlab_match.group(2)

    # Unrecognized URL format
    return None