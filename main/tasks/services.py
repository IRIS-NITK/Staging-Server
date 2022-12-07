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

# get environment variables
PATH_TO_HOME_DIR = os.environ.get('PATH_TO_HOME_DIR') | "~/stage_repo/HOME_DIR/" # path to main repo where all the git repos are stored
DEFAULT_BRANCH = os.environ.get('DEFAULT_BRANCH') | "main" # default branch to checkout

def pull_git(url, org_name, repo_name):
    # get name of repo
    repo_name = url.split('/')[-1].split('.')[0]
    # main or master ? -> DEFAULT_BRANCH
    # check if org exists
    if os.path.exists(f"{PATH_TO_HOME_DIR}/{org_name}"):
        # org exists, check if repo exists
        if os.path.exists(f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}"):
            # if repo already exists, we just pull latest changes 
            print("Repo already exists, pulling latest changes")
            res = run(
                ['git', 'pull'],
                stdout=PIPE,
                stderr=PIPE,
                cwd = f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{DEFAULT_BRANCH}/{repo_name}"
            )
            if res.returncode != 0:
                return False, res.stderr.decode('utf-8')
            return True, res.stdout.decode('utf-8')
        else:
            # repo does not exist , could be a new repo , so clone it
            os.mkdirs(f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{DEFAULT_BRANCH}")
            print("Repo does not exist, cloning it for the first time")
            res = run(
                ['git', 'clone', url],
                stdout=PIPE,
                stderr=PIPE,
                cwd=f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{DEFAULT_BRANCH}"
            )
            if res.returncode != 0:
                return False, res.stderr.decode('utf-8')
        return True, res.stdout.decode('utf-8')
    else:
        os.mkdirs(f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{DEFAULT_BRANCH}")
        print("Org does not exist, cloning it for the first time")
        res = run(
            ['git', 'clone', url],
            stdout=PIPE,
            stderr=PIPE,
            cwd=f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{DEFAULT_BRANCH}"
        )
        if res.returncode != 0:
            return False, res.stderr.decode('utf-8')
        return True, res.stdout.decode('utf-8')


def get_git_branches(repo_name):
    print("Getting branches")
    res = run(
        ['git', 'branch', '-a'],
        stdout=PIPE,
        stderr=PIPE,
        cwd=f"{PATH_TO_HOME_DIR}/{repo_name}/{DEFAULT_BRANCH}/{repo_name}"
    )
    if res.returncode != 0:
        return False, res.stderr.decode('utf-8')
    return True, res.stdout.decode('utf-8')

def checkout_git_branch(repo_name, org_name, branch_name):
    print(f"Switching to branch : {branch_name}")
    res = run(
        ['git', 'checkout', branch_name],
        stdout=PIPE,
        stderr=PIPE,
        cwd=f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{DEFAULT_BRANCH}/{repo_name}"
    )
    if res.returncode != 0:
        return False, res.stderr.decode('utf-8')
    return True, res.stdout.decode('utf-8')

def start_db_conatiner():
    # TODO: add support for other databases
    pass 

def start_web_container(org_name, repo_name, git_branch, docker_image, external_port, internal_port = 80, src_code_dir = None, dest_code_dir = None):
    """
    src_code_dir : code that needs to be mounted in the container , path is relative to one folder outside the git repo
    internal_port : port on which the container is running
    external_port : port on which the container is to be exposed

    """
    # src_code_dir is a list of directories that need to be bind mounted in the container
    # This command is run in the branch of the git repo
    if dest_code_dir:
        res = run(
            [
                'docker', 'run', '-d', # run in detached mode
                '-p', f'{external_port}:{internal_port}', # expose port
                f'-v "{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/{src_code_dir}:{dest_code_dir}"', # bind mount
                f'{docker_image}'
            ],
            stdout=PIPE,
            stderr=PIPE,
        )
    else:
        res = run(
            ['docker', 'run', '-d', '-p', f"{external_port}:{internal_port}", docker_image],
            stdout=PIPE,
            stderr=PIPE
        )
    if res.returncode != 0:
        return False, res.stderr.decode('utf-8')
    # return container id
    return True, res.stdout.decode('utf-8')


def deploy_from_git(url, repo_name, org_name, branch_name, docker_image , external_port, internal_port = 80,  src_code_dir = None , dest_code_dir = None):
    # pull git repo
    result, msg = pull_git(url)
    if not result:
        return False, msg 
    
    # get branches
    res, branches  = get_git_branches(repo_name)
    if not res[0]:
        return False, res[1]
    
    # check if branch exists
    if branch_name not in branches:
        return False, "Branch does not exist in the git repository"
    
    # checkout branch
    res = checkout_git_branch(repo_name, branch_name)
    if not res[0]:
        return False, res[1]
    
    # check if branch was already deployed previously
    if branch_name not in os.listdir(f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}"):
        # branch was not deployed previously
        # create a new directory for the branch
        os.mkdir(f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}")
        # copy the code from the default branch to the new branch
        res = run(
            ['cp', '-r', f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{DEFAULT_BRANCH}/{repo_name}/{src_code_dir}", f"{PATH_TO_HOME_DIR}/{org_name}/{repo_name}/{branch_name}/{src_code_dir}"],
            stdout=PIPE,
            stderr=PIPE
        )

    # start container 
    res, container_id = start_web_container(docker_image, external_port, internal_port,org_name, 
                                            repo_name, branch_name, docker_image, external_port, internal_port = 80, 
                                            src_code_dir = src_code_dir, dest_code_dir = dest_code_dir)
    if not res:
        return False, container_id
    return True, container_id
    
    



    
        