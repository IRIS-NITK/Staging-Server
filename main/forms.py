from django import forms
from .models import DeployTemplate

class DeployTemplateForm(forms.ModelForm):
    class Meta:
        model = DeployTemplate
        fields = ('name','social_type', 'organisation_or_user', 'git_repo_url', 'access_token', 'default_branch', 'docker_image', 'docker_network', 'docker_volumes', 'internal_port', 'dockerfile_path')

        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'organisation_or_user': forms.TextInput(attrs={'class': 'form-control'}),
            'git_repo_url': forms.URLInput(attrs={'class': 'form-control'}),
            'access_token': forms.PasswordInput(attrs={'class': 'form-control'}),
            'default_branch': forms.TextInput(attrs={'class': 'form-control'}),
            'docker_image': forms.TextInput(attrs={'class': 'form-control'}),
            'docker_network': forms.TextInput(attrs={'class': 'form-control'}),
            'docker_volumes': forms.Textarea(attrs={'class': 'form-control'}),
            'internal_port': forms.NumberInput(attrs={'class': 'form-control'}),
            'dockerfile_path': forms.TextInput(attrs={'class': 'form-control'}),
        }