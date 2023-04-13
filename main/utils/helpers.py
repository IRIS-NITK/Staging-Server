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
    if os.path.isfile(file_path):
        oldfile = True
    logger = open(file_path, "a", encoding='UTF-8')
    if oldfile:
        logger.write(f"\n{datetime.datetime.now()} : Logger Initiated\n")
    return logger

def exec_commands(commands,
                  logger,
                  err,
                  cwd=None,
                  print_stderr=False,
                  logger_not_file=False
                  ):
    """
    Executes commands given in as an array.
    """
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
                logger.close()
                return False, (err + '\n' + res.stderr.decode('utf-8'))
            logger.close()
            return False, err
        pretty_print(logger, res.stdout.decode('utf-8'), logger_not_file)
        return True, ""

def delete_directory(path):
    """
    deletes the specified directory
    """
    try:
        shutil.rmtree(path)
    except Exception as exception:  # pylint: disable=broad-exception-caught
        return False, f"Error in removing directory : {path}\n" + str(exception)
    return True, ""
