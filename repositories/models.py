from django.db import models
from django.contrib.auth.models import User

class Repository(models.Model):
    STATUS_PENDING = "PENDING"
    STATUS_SUCCESS = "SUCCESS"
    STATUS_ERROR="ERROR"
    STATUS_OPTIONS = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_ERROR, "Error"),
    ]
    deployer = models.ForeignKey(User, on_delete=models.CASCADE)
    repo_git_url = models.URLField(max_length=255, blank=True)
    repo_name = models.TextField()
    repo_username = models.TextField(blank=True)
    access_token = models.TextField(max_length=50, blank=True, null=True)

    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)
    status = models.TextField(choices=STATUS_OPTIONS, default=STATUS_PENDING)

    dockerfile_path = models.TextField(blank=True)
    app_env_vars = models.TextField(blank=True, null=True)
    app_env_db_host_key = models.TextField(blank=True, default="DEV_DB_HOST")
    db_image = models.TextField(blank=True)
    db_env_vars = models.TextField(blank=True, null=True)
    internal_port = models.IntegerField(default=80)
    deployments = models.PositiveIntegerField(default=0)