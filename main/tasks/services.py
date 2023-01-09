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


def pull_git(url, token, org_name, repo_name, branch_name = DEFAULT_BRANCH):
    
    # get name of repo
    # repo_name = url.split('/')[-1].split('.')[0]
    # main or master ? -> DEFAULT_BRANCH
    # check if org existss
    log_file = f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/{branch_name}.txt"
    if os.path.exists(f"{PATH_TO_HOME_DIR}/{org_name}"):
        # org exists, check if repo exists
        if os.path.exists(f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}"):
            
            try:
                f = open(log_file,"a")
            except FileNotFoundError:
                f = open(log_file,"w")
                f.write(f"{datetime.datetime.now()}\nStarting deployment\n")
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

def pull_git_changes(url, token = None, org_name = None, repo_name = None, branch_name = DEFAULT_BRANCH):
    user_name, repo_name = get_repo_info(url)
    org_name = user_name
    log_file = f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/{branch_name}.txt"
    DEFAULT_log_file = f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/DEFAULT_BRANCH/DEFAULT_BRANCH.txt"
    ## TODO : pull and checkout also needs access tokens 
    # Check if repository exists
    if os.path.exists(f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}"):       
        # Repository exists , check if branch exists
        if os.path.exists(f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}"):
            # Branch exists , pull latest changes
            logs = open(log_file,"a")
            logs.write(f'\n{datetime.datetime.now()} -> \tPulling latest changes from branch {branch_name}\n')

            res = subprocess.run(
                ['git', 'pull'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd = f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/{repo_name}"
            )

            if res.returncode != 0:
                logs.write(f'\n{datetime.datetime.now()} -> \tError while pulling latest changes from branch {branch_name}\n{res.stderr.decode("utf-8")}\nExited')
                logs.close()
                return False, res.stderr.decode('utf-8')

            logs.write(f'\n{datetime.datetime.now()} -> \tSuccessfully pulled latest changes from branch {branch_name}\n')
            logs.close()
            return True, res.stdout.decode('utf-8')

        else:
            # Branch does not exist , could be a new branch  
            # Pull latest changes from default branch
            res = subprocess.run(
                ['git', 'checkout', branch_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/DEFAULT_BRANCH/{repo_name}"
            )

            if res.returncode != 0:
                return False, res.stderr.decode('utf-8')
                
            res = subprocess.run(
                ['git', 'pull'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/DEFAULT_BRANCH/{repo_name}"
            )

            if res.returncode != 0:
                return False, res.stderr.decode('utf-8')

            os.makedirs(f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}")
            logs = open(log_file,"w")
            logs.write(f'\n{datetime.datetime.now()} -> \tBranch {branch_name} does not exist locally, pulling it\n')
            # copy latest changes to branch direcotry
            res = subprocess.run(
                ['cp', '-r', f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/DEFAULT_BRANCH/{repo_name}/.", f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/{repo_name}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd = f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/DEFAULT_BRANCH/{repo_name}"
            )

            if res.returncode != 0:
                logs.write(f'\n{datetime.datetime.now()} -> \tError while creating branch {branch_name}\n{res.stderr.decode("utf-8")}\nExited')
                logs.close()
                return False, res.stderr.decode('utf-8')
            
            logs.write(f'\n{datetime.datetime.now()} -> \tSuccessfully created branch {branch_name} locally\n')
            logs.close()
            return True, res.stdout.decode('utf-8')
    else:
        temp_logging_text = ""
        if not os.path.exists(f"{PATH_TO_HOME_DIR}/{org_name}"):
            temp_logging_text = f'\n{datetime.datetime.now()} -> \tOrganization {org_name} does not exist locally, creating it\n'
            os.makedirs(f"{PATH_TO_HOME_DIR}/{org_name}")

        # org exists , repo does not exist , could be a new repo , so clone it
        os.makedirs(f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/DEFAULT_BRANCH")
        temp_logging_text += f'\n{datetime.datetime.now()} -> \tRepository {repo_name} does not exist locally, creating it\n'

        # repo_url = "https://oauth2:"+token+"@github.com/"+user_name+"/"+repo_name+".git"
        
        if token:
            url = f'https://{user_name}:{token}@github.com/{user_name}/{repo_name}.git'

        parent_dir = f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/DEFAULT_BRANCH"
        local_dir = os.path.join(parent_dir, repo_name)

        res = run(
            ['git', 'clone', url , local_dir],
            stdout=PIPE,
            stderr=PIPE,
        )
        temp_logging_text += f'\n{datetime.datetime.now()} -> \tRepository {repo_name} does not exist locally, cloning it\n'
        if res.returncode != 0:
            return False, res.stderr.decode('utf-8')

        os.makedirs(f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}")
        try:
            logs = open(log_file,"a")
        except:
            logs = open(log_file,"w")
        logs.write(temp_logging_text)
        logs.write(f'\n{datetime.datetime.now()} -> \tBranch {branch_name} does not exist locally, creating it\n')
        
        # copy latest changes to branch direcotry
        res = subprocess.run(
            ['git', 'checkout', branch_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd = f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/DEFAULT_BRANCH/{repo_name}"
        )
        if res.returncode != 0:
            logs.write(f'\n{datetime.datetime.now()} -> \tError while creating branch {branch_name}\n{res.stderr.decode("utf-8")}\nExited')
            return False, res.stderr.decode('utf-8')
        
        logs.write(f'\n{datetime.datetime.now()} -> \tSuccessfully pulled latest changes from branch {branch_name}\n')
        # copy latest changes to branch direcotry
        res = subprocess.run(
            ['cp', '-r', f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/DEFAULT_BRANCH/{repo_name}/.", f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/{repo_name}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd = f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/DEFAULT_BRANCH/{repo_name}"
        )
        if res.returncode != 0:
            logs.write(f'\n{datetime.datetime.now()} -> \tError while creating branch {branch_name}\n{res.stderr.decode("utf-8")}\nExited')
            return False, res.stderr.decode('utf-8')
        logs.write(f'\n{datetime.datetime.now()} -> \tSuccessfully copied changes to branch {branch_name} locally\n')
        return True, res.stdout.decode('utf-8') 

def get_git_branches(repo_name, org_name):
    # log_file = f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{default_branch}/{branch_name}.txt"
    # f = open(log_file,"a")
    # f.write("Getting branches\n")
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
    log_file = f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/{branch_name}.txt"
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
        res = run(["docker","rm","-f",remove_container],stdout=PIPE,stderr=PIPE)
        if res.returncode != 0:
            return False, res.stderr.decode('utf-8')
    
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
            absolute_path = f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{remove_branch_dir}/{repo_name}"
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
    
    # yield "Clean up complete\n"
    return True, "Clean up complete"

@shared_task(bind=True)
def deploy_from_git_template(self, url, token = None, social = None, org_name = None, repo_name = None, branch_name = DEFAULT_BRANCH, internal_port = 80, external_port = 3000, docker_image = None, dockerfile_path = None, docker_volumes = {}, docker_env_variables = {}, default_branch = "main", docker_network = None):
    log_file = f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/{branch_name}.txt"
    
    # pull git repo
    res, msg = pull_git_changes(
        url=url,
        token=token,
        org_name=org_name,
        repo_name=repo_name,
        branch_name=branch_name,
    )

    temp_org_name, temp_repo_name = get_repo_info(url=url)
    if not org_name:
        org_name = temp_org_name
    if not repo_name:
        repo_name = temp_repo_name

    if not res:
        return False, msg
    
    logs = open(log_file,'a')
    
    if docker_image != None:
        logs.write(f"Searching for Docker image : {docker_image}\n")
        res = run(
            ['docker', 'inspect', docker_image],
            stdout=PIPE,
            stderr=PIPE
        )
        if res.returncode != 0:
            logs.write("Docker image not found\n")
            docker_image = None

    if docker_image == None:
        if dockerfile_path == None:
            logs.write("Dockerfile not provided\n")
            logs.close()
            return False, "Dockerfile not provided"
        logs.write(f"Docker image not provided, building image from {dockerfile_path}\n")
        docker_image = f"{org_name}/{repo_name}:{branch_name}"
        res = run(
            ['docker', 'build', '-t', docker_image, "."],
            stdout=PIPE,
            stderr=PIPE,
            cwd=f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/{repo_name}"
        )
        if res.returncode != 0:
            logs.write("Error while building docker image\ndeploy_from_git_template->run->docker build\n")
            logs.close()
            return False, "Error while building docker image\n" + res.stderr.decode('utf-8')
        else:
            logs.write(f"Docker image built successfully\ntagged : {docker_image}\n")
    
    logs.write(f"Starting container from image : {docker_image}\n")
    prefix = "iris_template"
    container_name = f"{prefix}_{org_name}_{repo_name}_{branch_name}"
    check_container_exists = run(["docker","container","inspect",container_name],stdout=PIPE,stderr=PIPE)

    
    if check_container_exists.returncode == 0:
        logs.write(f"Container already exists : {container_name}\n")
        logs.write(f"Removing existing container : {container_name}\n")
        res = run(
            ["docker","rm","-f",container_name],
            stdout=PIPE,
            stderr=PIPE
        )
        if res.returncode != 0:
            logs.write("Error while removing existing container\ndeploy_from_git_template->run->docker rm\n")
            logs.close()
            return False, "Error while removing existing container\n" + res.stderr.decode('utf-8')
        logs.write(f"Existing container removed : {container_name}\n")
    
    logs.write(f"Starting container : {container_name}\n")
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
        logs.write(f"Error while starting container : {container_name}\n")
        logs.close()
        return False, container_id
    
    logs.write(f"Container started successfully \ncontainer name : {container_name}\ncontainer id : {container_id}\n")
    return True, container_id
    # res = run(
    #         ["sudo", "bash", NGINX_ADD_CONFIG_SCRIPT,str(branch_name), str(external_port)],
    #         stdout=PIPE,
    #         stderr=PIPE,
    #     )

@shared_task(bind=True)
def deploy_from_git(self, token, url, social, org_name, repo_name, branch_name, internal_port = 3000,  src_code_dir = None , dest_code_dir = None, docker_image=None, volumes = {}, DEFAULT_BRANCH = "master"):
    

    log_file = f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/{branch_name}.txt"
    # pull git repo
    result,msg = pull_git(url,token,repo_name=repo_name, org_name=org_name, branch_name=branch_name )
    f = open(log_file,'a')
    f.write(msg)
    if not result:
        f.write(msg)
        f.close()
        return False, msg 


    # get branches
    res, branches  = get_git_branches(repo_name, org_name=org_name)
    if not res:
        f.write(branches)
        f.close()
        return False, branches
        
    
    # check if branch exists
    if branch_name not in branches:
        return False, "Branch does not exist in the git repository"
    
    # checkout branch
    res, msg = checkout_git_branch(repo_name=repo_name, org_name=org_name, branch_name=branch_name)

    if not res[0]:
        f.write(msg)
        f.close()
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
            f.write(res.stdout.decode('utf-8')+"\n")
            f.close()
            return
    
    
    # # org_name, repo_name, branch_name, docker_image, external_port, internal_port = 80, src_code_dir = None, dest_code_dir = None
    prefix = "iris"
    container_name = f"{prefix}_{org_name}_{repo_name}_{branch_name}"
    check_container_exists = run(["docker","container","inspect",container_name],stdout=PIPE,stderr=PIPE)
    external_port = find_free_port()
    env_variables = {}

    if org_name == "NITK-IRIS":
        src = f'{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/{repo_name}/' + "config/initializers"
        path_to_nitk_setting = os.getenv("PATH_TO_NITK_SETTING")
        path_to_secret_token = os.getenv("PATH_TO_SECRET_TOKEN")
        res = run(["cp",path_to_nitk_setting,src],stdout=PIPE,stderr=PIPE)
        res = run(["cp",path_to_secret_token,src],stdout=PIPE,stderr=PIPE)
        src = f'{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/{repo_name}/'
        dest = "/iris-data/" 
        volumes = {
             src : dest,
        }
        env_variables = {
            "RAILS_ENV": "development"
        }

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
            f.close()
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
    f.write(res.stdout.decode('utf-8')+"\n")
    if res.returncode != 0: 
        f.close()
        return False, res.stderr.decode('utf-8')
    f.close()
    return True, "Success"

def get_repo_info(url):
    "Return org/username , repo name from a GitHub or GitLab URL."
    github_match = re.match(r'(?:https?://)?github.com/(.+)/(.+)', url)
    if github_match:
        return (github_match.group(1), github_match.group(2))

    gitlab_match = re.match(r'(?:https?://)?gitlab.com/(.+)/(.+)', url)
    if gitlab_match:
        return (gitlab_match.group(1), gitlab_match.group(2))

    # Unrecognized URL format
    return (None, None)

