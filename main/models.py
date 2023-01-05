from django.db import models

class RunningInstance(models.Model):
    STATUS_PENDING = "PENDING"
    STATUS_SUCCESS = "SUCCESS"
    STATUS_ERROR="ERROR"
    STATUS_ONGOING="DEPLOYING"
    STATUS_OPTIONS = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_ERROR, "Error"),
        (STATUS_ONGOING, "Deploying")
    ]
    branch = models.TextField()
    owner = models.TextField()
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)
    status = models.TextField(choices=STATUS_OPTIONS, default=STATUS_PENDING)
    organisation = models.TextField()
    repo_name = models.TextField()
    social = models.TextField()
    
class DeployTemplate(models.Model):
    social_type = models.TextField(
        choices=[
            ("github", "Github"),
            ("gitlab", "Gitlab"),
            ("other", "Other")
        ]
    )

    
    organisation_or_user = models.TextField("Organisation or User", max_length=100)
    git_repo_url = models.URLField("Git URL", max_length=200)
    access_token = models.TextField("Access Token", max_length=50)
    default_branch = models.TextField("Default Branch", default="main", max_length=50) 
    
    docker_image = models.TextField("Docker Image", default="ubuntu:latest", max_length=100)
    docker_network = models.TextField("Docker Network", default="bridge", max_length=100)
    docker_volumes = models.TextField("Docker Volumes", default="{}", max_length=500)
    internal_port = models.IntegerField("Internal Port", default="80")

    dockerfile_path = models.TextField("Dockerfile Path", blank=True, max_length=100)