from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from allauth.socialaccount.models import SocialToken
from github import Github
import gitlab

# Create your views here.
@login_required(login_url='/accounts/login/')
def home(response):
    # Example of how to get the access token for a particular provider
    # PyGithub: https://pygithub.readthedocs.io/en/latest/introduction.html
    gh_access_token_set = SocialToken.objects.filter(account__user=response.user, account__provider='github')
    if (len(gh_access_token_set) == 0):
        print("No Github Access Token")
    else:
        g = Github(gh_access_token_set.first().__str__())
        print("1", g.get_user().login)
        for repo in g.get_user().get_orgs():
                print(repo.name)

    gl_access_token_set = SocialToken.objects.filter(account__user=response.user, account__provider='gitlab')
    if (len(gl_access_token_set) == 0):
        print("No Gitlab Access Token")
    else:
        # Python Gitlab: https://python-gitlab.readthedocs.io/en/stable/
        gl = gitlab.Gitlab(url='https://git.iris.nitk.ac.in', oauth_token=gl_access_token_set.first().__str__())
        gl.auth()
        print("2", gl.user.emails.list())
    return render(response, "main/home.html")

    
