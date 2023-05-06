from django.db import models

class RunningInstance(models.Model):
    STATUS_PENDING = "PENDING"
    STATUS_SUCCESS = "SUCCESS"
    STATUS_ERROR="ERROR"
    STATUS_ONGOING="DEPLOYING"
    STATUS_STOPPED="STOPPED"
    STATUS_OPTIONS = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_ERROR, "Error"),
        (STATUS_STOPPED, "Stopped"),
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
    exposed_port = models.IntegerField(default=3000)
    dockerfile_path = models.TextField(blank=True)
    internal_port = models.IntegerField(default=80)
    deployed_url = models.URLField(max_length=255, blank=True)
    project_url = models.URLField(max_length=255, blank=True)
    app_container_name = models.TextField(blank=True)
    db_container_name = models.TextField(blank=True)
    app_docker_image = models.TextField(blank=True)
    db_docker_image = models.TextField(blank=True)
class DeployTemplate(models.Model):
    social_type = models.TextField(
        choices=[
            ("github", "Github"),
            ("gitlab", "Gitlab"),
            ("other", "Other")
        ]
    )

    name = models.TextField("Name", max_length=100)
    organisation_or_user = models.TextField("Organisation or User", max_length=100)
    git_repo_url = models.URLField("Git URL", max_length=200)
    access_token = models.TextField("Access Token", max_length=50, blank=True, null=True)
    default_branch = models.TextField("Default Branch", default="main", max_length=50) 
    
    docker_image = models.TextField("Docker Image", max_length=100, blank=True)
    docker_network = models.TextField("Docker Network", default="bridge", max_length=100)
    docker_volumes = models.TextField("Docker Volumes", default="{}", max_length=500)
    docker_env_vars = models.TextField("Docker Environment Variables", default="{}", max_length=500)
    internal_port = models.IntegerField("Internal Port", default="80")

    dockerfile_path = models.TextField("Dockerfile Path", blank=True, max_length=100)

    