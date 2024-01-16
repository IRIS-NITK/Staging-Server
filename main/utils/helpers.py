"""
Helper functions
"""
import os
import datetime
import shutil
import subprocess



def pretty_print(logs,
                 text,
                 logger_not_file=False
                 ):
    """
    Printing to log file with timestamp
    """
    if logger_not_file:
        logs = logs + '\n' + text
        return
    logs.write(f"{datetime.datetime.now()} : {text}\n")

def initiate_logger(file_path):
    """
    opens log file, creates the file / directories for it if they doesn't exist.
    """
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    oldfile=False
    if os.path.isfile(file_path):
        oldfile = True
    logger = open(file_path, "a", encoding='UTF-8')
    if oldfile:
        logger.write(f"\n{datetime.datetime.now()} : Logger Initiated\n")
    return logger

def exec_commands(commands,
                  err="",
                  logger="",
                  cwd=None,
                  print_stderr=False,
                  logger_not_file=False
                  ):
    """
    Executes commands given in as an array.
    """

    print(commands) # Log the commands being executed
    
    result = ""
    for command in commands:
        res = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            check=False
        )
        if res.returncode != 0:
            pretty_print(logger, err, logger_not_file)
            if print_stderr:
                pretty_print(logger, res.stderr.decode(
                    'utf-8'), logger_not_file)
                return False, (err + '\n' + res.stderr.decode('utf-8'))
            return False, err
        result = result + res.stdout.decode('utf-8') +"\n"
        pretty_print(logger, result, logger_not_file)
    if print_stderr:
        return True, result
    return True, "executed Successfully"

def delete_directory(path):
    """
    deletes the specified directory
    """
    try:
        shutil.rmtree(path)
    except Exception as exception:  # pylint: disable=broad-exception-caught
        return False, f"Error in removing directory : {path}\n" + str(exception)
    return True, ""


def generate_deployment_id(org_name, project, branch, domain, subdomain_prefix):
    """
    generates deployment id for a specific deployment.
    """
    return (f"{org_name.lower()[0:9]}_{project.lower()[0:9]}_{branch.lower()}")[0:63-len(subdomain_prefix)-1-1-len(domain)]


def get_app_container_name(prefix, deployment_id):
    """
    generates container name for a specific deployment.
    """
    return f"{prefix}_{deployment_id}"

def get_db_container_name(prefix, deployment_id):
    """
    generates db container name for a specific deployment.
    """
    return f"{prefix}_DB_{deployment_id}"