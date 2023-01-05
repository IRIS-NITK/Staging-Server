from django import forms
from .models import DeployTemplate

class DeployTemplateForm(forms.ModelForm):
    class Meta:
        model = DeployTemplate
        fields = ('social_type', 'organisation_or_user', 'git_repo_url', 'access_token', 'default_branch', 'docker_image', 'docker_network', 'docker_volumes', 'internal_port', 'dockerfile_path')