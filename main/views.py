"""
views for main
"""
import os
import subprocess
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, StreamingHttpResponse
from django.shortcuts import render, redirect
from django.core.exceptions import ObjectDoesNotExist
from main.models import RunningInstance
from django.template import Context, loader
from .forms import DeployTemplateForm
from .models import DeployTemplate

from dotenv import load_dotenv

load_dotenv()
PREFIX = os.getenv("PREFIX", "staging")
PATH_TO_HOME_DIR = os.getenv("PATH_TO_HOME_DIR")


response_header = loader.get_template("response_header.html")


@login_required
def container_logs(request, pk):
    # pylint: disable=unused-argument
    instance = RunningInstance.objects.get(pk=pk)
    container_name = f"{PREFIX}_{instance.organisation.lower()}_{instance.repo_name.lower()}_{instance.branch.lower()}"
    command = ["docker", "logs", "-f", container_name]

    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def generate_stream():
        yield response_header.render({"purpose": "Starting"})
        yield "<pre><code >"
        while process.poll() is None:
            output = process.stdout.readline()
            logs = output.decode("utf-8")
            yield logs
        output, errors = process.communicate()
        if errors:
            logs = errors.decode("utf-8")
            yield logs

    response = StreamingHttpResponse(generate_stream())
    del response["Content-Length"]
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


@login_required
def instance_logs(request, pk):
    try:
        instance = RunningInstance.objects.get(pk=pk)
        log_file_name = f"{PATH_TO_HOME_DIR}/{instance.organisation}/{instance.repo_name}/{instance.branch}/{instance.branch}.txt"
        with open(log_file_name, "r", encoding='UTF-8') as file:
            data = file.read()
        context = {'data': data, 'instance': instance}
        return render(request, 'logs.html', context)
    except:  # pylint: disable=bare-except
        return render(request, 'error_log.html')


@login_required
def homepage(request):
    return render(request, "homepage.html")
