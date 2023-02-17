from django.db import models

# Create your models here.

class Template(models.Model):
    vcs = models.TextField(
        choices=[
            ("github", "github"), 
            ("gitlab", "gitlab"),
            ("git.iris", "git.iris")
        ]
    )

    name = models.TextField("Name", max_length = 100)
    user_name = models.TextField("Organisation or User", max_length = 100)
    repo_name = models.TextField("Repository Name", max_length = 100)
    git_url = models.URLField("Git URL", max_length = 200)
    access_token = models.TextField("Access Token", max_length = 100, null = True, blank = True)
    branch = models.TextField("Branch", max_length = 100)
    default_branch = models.TextField("Default Branch", default = "main", max_length = 100)  
    

    docker_image = models.TextField("Docker Image", max_length = 100, null = True, blank=True)
    docker_network = models.TextField("Docker Network", default = "bridge", max_length = 100)
    docker_volumes = models.TextField("Docker Volumes", default = "{}", max_length = 500)
    docker_env_vars = models.TextField("Docker Environment Variables", default = "{}", max_length = 500)
    internal_port = models.IntegerField("Internal Port", default = "80")

    dockerfile_path = models.TextField("Dockerfile Path", default = "Dockerfile", null = True, blank = True, max_length = 100)