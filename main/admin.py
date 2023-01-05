from django.contrib import admin
from main.models import RunningInstance, DeployTemplate
# Register your models here.
admin.site.register(RunningInstance)
admin.site.register(DeployTemplate)