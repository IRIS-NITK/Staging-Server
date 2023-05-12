"""
views for main
"""
import os
import socket
import json
import http.client
import re
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.template import loader
from dotenv import load_dotenv
from django.http import HttpResponseRedirect
import docker
import threading
from channels.generic.websocket import WebsocketConsumer
from main.models import RunningInstance
from main.services import clean_logs

load_dotenv()
PREFIX = os.getenv("PREFIX", "staging")
PATH_TO_HOME_DIR = os.getenv("PATH_TO_HOME_DIR")
DOCKER_SOCKET_HOST = os.getenv("DOCKER_SOCKET_HOST","socat")
DOCKER_SOCKET_PORT = os.getenv("DOCKER_SOCKET_PORT","2375")

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


def is_valid_json(json_str):
    """
    Check if a string is valid JSON.
    """
    try:
        json.loads(json_str)
        return True
    except json.JSONDecodeError:
        return False
                
class LogsConsumer(WebsocketConsumer):
    """
    streams container logs via a websocket.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = docker.APIClient()
        self.container_name = None
        self.kill_send = False
        self.stream = None
        self.thread = None
    
    def connect(self):
        self.accept()
        try:
            instance = RunningInstance.objects.get(
                pk=self.scope['url_route']['kwargs']['pk'])
            self.container_name = instance.app_container_name
        except:  # pylint: disable=bare-except
            self.send("Could not find the Instance.")
            return self.disconnect(self)
        try:
            self.stream = self.client.logs(self.container_name, stream=True, follow=True)
        except  Exception as error:  # pylint: disable=bare-except
            self.send(f'An Error occurred:{type(error).__name__} – {redact_url(str(error))}')
            return self.disconnect(self)
        self.thread = threading.Thread(target=self.send_logs)
        self.thread.start()

    def send_logs(self):
        for data in self.stream:
            if self.kill_send:
                break
            self.send(data.decode())

    def disconnect(self, code):
        self.kill_send = True
        return super().disconnect(code)


def redact_url(text: str) -> str:
    """
    for redacting any URL from being printed to the user while displaying errors.
    """
    url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    return url_pattern.sub("[REDACTED URL]", text)

class ConsoleConsumer(WebsocketConsumer):
    """
    websocket for container Console.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.host=DOCKER_SOCKET_HOST
        self.port=DOCKER_SOCKET_PORT
        self.socket_url=f'tcp://{self.host}:{self.port}'
        self.client = docker.APIClient(base_url=self.socket_url)
        self.exec_id = None
        self.socket = None
        self.container_name= None
        self.conn = None
        self.stop_thread= False
        self.thread = None

    def connect(self):
        self.accept()
        try:
            instance = RunningInstance.objects.get(
                pk=self.scope['url_route']['kwargs']['pk'])
            self.container_name = instance.app_container_name
        except:  # pylint: disable=bare-except
            self.send("Could not find the Instance.")
            return self.disconnect(self)
        cmd = '/bin/bash'
        try:
            self.exec_id = self.client.exec_create(self.container_name, cmd, stdout=True, stderr=True, stdin=True, tty=True)
            self.socket = socket.create_connection((self.host, self.port))
            http_conn = http.client.HTTPConnection(self.host, self.port)
            http_conn.sock = self.socket
            params = json.dumps({'Detach': False, 'Tty': True})
            headers = {
                'User-Agent': 'Docker-Client',
                'Content-Type': 'application/json',
                'Connection': 'Upgrade',
                'Upgrade': 'tcp'
            }
            http_conn.request('POST', f'/exec/{self.exec_id["Id"]}/start', body=params, headers=headers)
            _ = http_conn.getresponse()
        except  Exception as error:  # pylint: disable=bare-except
            self.send(f'An Error occurred:{type(error).__name__} := {redact_url(str(error))}')
            return self.disconnect(self)
        # Start a new thread to receive data from the container's socket
        self.thread = threading.Thread(target=self.receive_data_from_socket)
        self.send("\x1b[1;36m" + "-------IRIS Staging Server-------\n" + "\x1b[0m")
        self.send("\x1b[1;32m" + f"Successfully Connected to {instance.app_container_name} container\n" + "\x1b[0m")
        self.thread.start()

    def receive(self, text_data, *_):
        """
        Handle incoming data from the WebSocket.
        """
        self.socket.sendall(text_data.encode('ISO-8859-1'))

    def disconnect(self, code):
        """
        overriding disconnect of websocket to close thread and docker exec socket.
        """
        self.stop_thread=True
        self.socket.close()
        return super().disconnect(code)

    def receive_data_from_socket(self):
        """
        # Receive data from the container's socket and send it back to the WebSocket
        """
        while True:
            if self.stop_thread:
                break
            msg = self.socket.recv(1024)
            self.send(msg.decode('ISO-8859-1'))
