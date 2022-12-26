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
    