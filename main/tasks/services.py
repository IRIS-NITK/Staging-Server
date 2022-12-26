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

"""
from subprocess import PIPE, run
import os
from celery import shared_task
from main.models import RunningInstance
# from app.getport import find_free_port
from allauth.socialaccount.models import SocialToken
import sys
from dotenv import load_dotenv
from main.tasks.findfreeport import find_free_port

load_dotenv()
# from ..setup import PATH_TO_HOME_DIR
PATH_TO_HOME_DIR = os.getenv("PATH_TO_HOME_DIR")
DEFAULT_BRANCH = "main" # should be a config ideally
log_file = ""


def pull_git(url, org_name, repo_name):
    # get name of repo
    # repo_name = url.split('/')[-1].split('.')[0]
    # main or master ? -> DEFAULT_BRANCH
    # check if org exists
    if os.path.exists(f"{PATH_TO_HOME_DIR}/{org_name}"):
        # org exists, check if repo exists
        if os.path.exists(f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}"):
            # if repo already exists, we just pull latest changes 
            f = open(log_file,"a")
            f.write("Repo already exists, pulling latest changes\n")
            res = run(
                ['git', 'pull'],
                stdout=PIPE,
                stderr=PIPE,
                cwd = f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{DEFAULT_BRANCH}/{repo_name}"
            )
            if res.returncode != 0:
                f.write(res.stderr.decode('utf-8')+"\n")
                return False,res.stderr.decode('utf-8')
            f.write(res.stdout.decode('utf-8')+"\n")
            return True,res.stdout.decode('utf-8')
        else:
            # repo does not exist , could be a new repo , so clone it
            os.makedirs(f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{DEFAULT_BRANCH}")
            f = open(log_file,"a")
            f.write("Repo does not exist, cloning it for the first time\n")
            res = run(
                ['git', 'clone', url],
                stdout=PIPE,
                stderr=PIPE,
                cwd=f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{DEFAULT_BRANCH}"
            )
            if res.returncode != 0:
                f.write(res.stderr.decode('utf-8')+"\n")
                return False, res.stderr.decode('utf-8')
        f.write(res.stdout.decode('utf-8')+"\n")
        return True, res.stdout.decode('utf-8')
    else:
        os.makedirs(f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{DEFAULT_BRANCH}")
        f = open(log_file,"a")
        f.write("Org does not exist, cloning it for the first time\n")
        res = run(
            ['git', 'clone', url],
            stdout=PIPE,
            stderr=PIPE,
            cwd=f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{DEFAULT_BRANCH}"
        )
        if res.returncode != 0:
            f.write(res.stderr.decode('utf-8')+"\n")
            return False, res.stderr.decode('utf-8')
        f.write(res.stdout.decode('utf-8')+"\n")
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
        f.write(res.stderr.decode('utf-8')+"\n")
        return False, res.stderr.decode('utf-8')
    f.write(res.stdout.decode('utf-8')+"\n")
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
        f.write(res.stderr.decode('utf-8')+"\n")
        return False, res.stderr.decode('utf-8')
    f.write(res.stdout.decode('utf-8')+"\n")
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
        command.extend(["--env", *[f"{k}={v}" for k,v in db_env_variables.items()]])
    if network_name:
        command.extend(["--network", network_name])
    command.extend(["--detach", "--rm", db_image])

    res = run(
        command,
        stdout=PIPE,
        stderr=PIPE,
    )    
    if res.returncode != 0:
        return False, res.stderr.decode('utf-8')
    return True, res.stdout.decode('utf-8')

 

def start_web_container(org_name, repo_name, branch_name, docker_image, internal_port = 3000, src_code_dir = None, dest_code_dir = None):
    """
    src_code_dir : code that needs to be mounted in the container , path is relative to one folder outside the git repo
    internal_port : port on which the container is running
    external_port : port on which the container is to be exposed

    """
    # src_code_dir is a list of directories that need to be bind mounted in the container
    # This command is run in the branch of the git repo
    external_port = find_free_port()
    print(external_port)
    f = open(log_file,"a")
    container_name = "iris_dev"+branch_name
    running_instance = RunningInstance.objects.get(branch=branch_name,repo_name=repo_name,organisation=org_name)
    if dest_code_dir:
        f.write("Mounting code in container and starting it\n")
        res = run(
            [
                'docker', 'run', '-d', # run in detached mode
                '-p', f'{external_port}:{internal_port}', # expose port
                f'-v "{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/{src_code_dir}:{dest_code_dir}"',
                "--name",container_name, # bind mount
                f'{docker_image}'
            ],
            stdout=PIPE,
            stderr=PIPE,
        )
    else:
        f.write("Starting container")
        res = run(
            ['docker', 'run', '-d', '-p', f"{external_port}:{internal_port}", "--name", container_name, docker_image],
            stdout=PIPE,
            stderr=PIPE
        )
        if res.returncode != 0:
            running_instance.status = RunningInstance.STATUS_ERROR
            return False, res.stderr.decode('utf-8')
        else:
            running_instance.status = RunningInstance.STATUS_SUCCESS
    # return container id
    running_instance.save() 
    return True, res.stdout.decode('utf-8')


@shared_task(bind=True)
def deploy_from_git(self, token, url, social, org_name, repo_name, branch_name, internal_port = 3000,  src_code_dir = None , dest_code_dir = None, docker_image=None,DEFAULT_BRANCH = "main"):
    

    if branch_name == None:
        branch_name = "main"
    global log_file
    log_file = PATH_TO_HOME_DIR+"/"+org_name+"/"+repo_name+"/"+DEFAULT_BRANCH+"/"+branch_name+".txt"

    # pull git repo
    result,msg = pull_git(url,repo_name=repo_name, org_name=org_name)

    if not result:
        return False, msg 

    # get branches
    res, branches  = get_git_branches(repo_name, org_name=org_name)
    if not res:
        return False, branches
        
    
    # check if branch exists
    if branch_name not in branches:
        return False, "Branch does not exist in the git repository"
    
    # checkout branch
    res = checkout_git_branch(repo_name, branch_name=branch_name, org_name=org_name)
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
            res = run(
                ['cp', '-r', f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{DEFAULT_BRANCH}/{repo_name}/{src_code_dir}", f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/{src_code_dir}"],
                stdout=PIPE,
                stderr=PIPE
            )
    #copy log_file to particular directory
    source = PATH_TO_HOME_DIR+"/"+org_name+"/"+repo_name+"/"+DEFAULT_BRANCH+"/"+branch_name+".txt"
    dest = PATH_TO_HOME_DIR+"/"+org_name+"/"+repo_name+"/"+branch_name+"/"
    res = run(
            ['cp', source, f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/"],
                stdout=PIPE,
                stderr=PIPE
            )
    
    if res.returncode!=0:
        print(res.stdout.decode('utf-8'))

    image_name = ""
    docker_image = ""
    if social == 'gitlab':
        docker_image = "git-registry.iris.nitk.ac.in/iris-nitk/iris/iris-base-dev"
    else:
        image_name = org_name+"/"+repo_name+":"+branch_name
        docker_image = image_name.lower()
    # start container 

    checkimageexists = run(["docker","image","inspect",docker_image],stdout=PIPE,stderr=PIPE)

    if checkimageexists.returncode != 0:
        res = run(
            ['docker', 'build', '-t', docker_image, "."],
            stdout=PIPE,
            stderr=PIPE,
            cwd=f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/{repo_name}"
        )
        if res.returncode != 0:
            return False, res.stderr.decode('utf-8')
    
    # # org_name, repo_name, branch_name, docker_image, external_port, internal_port = 80, src_code_dir = None, dest_code_dir = None
    res, container_id = start_web_container(
        org_name=org_name,
        repo_name=repo_name,
        branch_name=branch_name,
        docker_image=docker_image,
        internal_port=internal_port,
        src_code_dir=src_code_dir,
        dest_code_dir=dest_code_dir
    )
    if not res:
        return False, container_id
    return True, container_id
