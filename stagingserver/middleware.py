# modified from https://github.com/pennersr/django-allauth/issues/420

import logging

from django.contrib.auth import logout
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone
from django.conf import settings

import requests, json
import gitlab
from allauth.socialaccount.models import SocialToken, SocialApp

def oauth_session_enforcement(get_response):
    """
    For any user that is authenticated via GitLab, we check that their token
    has not expired. If it has, we try to refresh it. If we can't refresh it, we log
    them out.
    """

    gitlab_provider = settings.SOCIALACCOUNT_PROVIDERS["gitlab"]
    logger = logging.getLogger(f"{__name__}.{oauth_session_enforcement.__name__}")
    gitlab_url=gitlab_provider["GITLAB_URL"]
    def middleware(request):
        if not hasattr(request, "user"):
            raise ImproperlyConfigured(
                "oauth_session_enforcement must be included in middlewares after "
                "django.contrib.auth.middleware.AuthenticationMiddleware or equivalent"
            )
        user = request.user
        try:
            social_token = SocialToken.objects.get(account__user_id=user.id)
        except SocialToken.DoesNotExist:
            # means our user was logged in via username and password so they can stay authenticated
            return get_response(request)
        if social_token.expires_at > timezone.now():
            return get_response(request)
        try:
            logger.info("Attempting to refresh expired access_token")
            social_app = SocialApp.objects.get(provider='gitlab')
            gl_client_id = social_app.client_id
            gl_secret = social_app.secret
            # Get the GitLab refresh token for the current user
            gl_refresh_token = social_token.token_secret
            # Make a POST request to the GitLab token endpoint to obtain a new access token
            token_url = '{gitlab_url}/oauth/token'.format(gitlab_url=gitlab_url)
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': gl_refresh_token,
                'client_id': gl_client_id,
                'client_secret': gl_secret,
            }
            response = requests.post(token_url, data=data)
            if(response.status_code != 200):
                logger.error("Failed to refresh expired access_token")
                logout(request)
                return get_response(request)
            response_json = json.loads(response.content)
            gl_access_token = response_json['access_token']
            gl_refresh_token = response_json['refresh_token']
            expires_in = response_json['expires_in']
            new_expiration_time = timezone.now() + timezone.timedelta(seconds=expires_in)
            social_token.expires_at = new_expiration_time
            # Update the GitLab access token for the current user
            social_token.token = gl_access_token
            social_token.token_secret = gl_refresh_token
            social_token.save()

            # Use the new access token to make API requests to GitLab
            gitlab_client = gitlab.Gitlab(
                url=gitlab_url,
                oauth_token=gl_access_token
            )
            gitlab_client.auth()
        except Exception as e:
            logger.exception("Failed to refresh expired access_token")
            logout(request)
        return get_response(request)
    return middleware

# ^_^ 