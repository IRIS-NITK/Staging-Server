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
from main.services import clean_logs, clean_up
from dotenv import load_dotenv
from django.http import HttpResponseRedirect
import chardet
import docker
import threading
import unicodedata
from channels.generic.websocket import WebsocketConsumer, AsyncWebsocketConsumer

load_dotenv()
PREFIX = os.getenv("PREFIX", "staging")
PATH_TO_HOME_DIR = os.getenv("PATH_TO_HOME_DIR")


response_header = loader.get_template("response_header.html")

@login_required
def instance_logs(request, pk):
    try:
        instance = RunningInstance.objects.get(pk=pk)
        log_file_name = f"{PATH_TO_HOME_DIR}/logs/{instance.organisation}/{instance.repo_name}/{instance.branch}/{instance.branch}.txt"
        with open(log_file_name, "r", encoding='UTF-8') as file:
            data = file.read()
        context = {'data': data, 'instance': instance}
        return render(request, 'logs.html', context)
    except:  # pylint: disable=bare-except
        return render(request, 'error_log.html')


@login_required
def archive_logs(request, pk):
    """
    cleans logs and saves them to the archive
    """
    try:
        instance = RunningInstance.objects.get(pk=pk)
    except:  # pylint: disable=bare-except
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    clean_logs(org_name=instance.organisation,
               repo_name=instance.repo_name, branch_name=instance.branch)
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


@login_required
def homepage(request):
    """
    rendering the view for Homepage.
    """
    return render(request, "homepage.html")

@login_required
def console(request, pk):
    """
    rendering the view for container console.
    """
    try:
        instance = RunningInstance.objects.get(pk=pk)
    except:  # pylint: disable=bare-except
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    return render(request, 'console.html', {'instance':instance})

@login_required
def container_logs(request, pk):
    """
    rendering the view for container logs.
    """
    try:
        instance = RunningInstance.objects.get(pk=pk)
    except:  # pylint: disable=bare-except
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    return render(request, 'container_logs.html', {'instance':instance})


class ConsoleConsumer(WebsocketConsumer):
    """
    websocket for container Console.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = docker.APIClient()
        self.exec_id = None
        self.socket = None
        self.container_name = None

    def connect(self):
        try:
            instance = RunningInstance.objects.get(
                pk=self.scope['url_route']['kwargs']['pk'])
        except:  # pylint: disable=bare-except
            self.close()
        container_name = instance.app_container_name
        cmd = ['/bin/bash']
        try:
            self.exec_id = self.client.exec_create(
                container_name, cmd, stdout=True, stderr=True, stdin=True, tty=True)
        except:  # pylint: disable=bare-except
            self.accept()
            self.send("Error connecting to container")
            self.send(Exception)
            self.close()
        self.socket = self.client.exec_start(
            self.exec_id, stream=True, socket=True, tty=True)
        self.socket._sock.settimeout(120)
        self.accept()
        self.send("Connected to the container Successfully.")
        # Start a new thread to receive data from the container's socket
        threading.Thread(target=self.receive_data_from_socket).start()

    def receive(self, text_data, *_):
        # Send data received from the WebSocket to the container's socket
        minicmd = text_data + "\n"
        self.socket._sock.send(minicmd.encode('utf-8'))

    def disconnect(self, *_):
        self.socket.close()

    def receive_data_from_socket(self):
        """
        # Receive data from the container's socket and send it back to the WebSocket
        """
        while True:
            try:
                for output in self.socket:
                    if output:
                        encoding = chardet.detect(output)['encoding']
                        output = output.decode(encoding)
                        output = ''.join(
                            ch for ch in output if unicodedata.category(ch)[0] != 'C')
                        self.send(output)
            except:  # pylint: disable=bare-except
                pass

class LogsConsumer(WebsocketConsumer):
    """
    streams container logs via a websocket.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = docker.APIClient()
        self.container_name = None

    def fetch_container_name(self, pk):
        """
        fetches container Name
        """
        try:
            instance = RunningInstance.objects.get(pk=pk)
            return instance.app_container_name
        except:  # pylint: disable=bare-except
            pass
        return False
    
    def connect(self):
        self.accept()
        pk= self.scope['url_route']['kwargs']['pk']
        self.container_name =  self.fetch_container_name(pk)
        if not self.container_name:
            self.send("There's been a error")
            self.close()
            return
        try:
            stream = self.client.logs(self.container_name, stream=True, follow=True)
        except:  # pylint: disable=bare-except
            self.send("Error connecting to container. It may not have been created yet.")
            self.close()
            return
        for data in stream:
            self.send(data.decode())
