"""
Helper functions
"""
import os
import datetime
import shutil
import subprocess
import hashlib

def hash_string_and_time(input_string):
    """
    Hashing branch name to shorten domain name
    """
    current_time = str(datetime.datetime.now())
    combined_string = input_string + current_time
    sha256_hash = hashlib.sha256()
    sha256_hash.update(combined_string.encode('utf-8'))
    hex_digest = sha256_hash.hexdigest()

    # Get the first 10 characters of the hash
    hash_result = hex_digest[:10]

    return hash_result

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
