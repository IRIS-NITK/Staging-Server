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
    Refresh only provider-specific tokens that need it. GitHub OAuth tokens are kept
    as-is and should not be treated like GitLab refreshable tokens.
    """

    gitlab_provider = settings.SOCIALACCOUNT_PROVIDERS.get("gitlab", {})
    logger = logging.getLogger(f"{__name__}.{oauth_session_enforcement.__name__}")
    gitlab_url = gitlab_provider.get("GITLAB_URL", "https://gitlab.com")

    def middleware(request):
        if not hasattr(request, "user"):
            raise ImproperlyConfigured(
                "oauth_session_enforcement must be included in middlewares after "
                "django.contrib.auth.middleware.AuthenticationMiddleware or equivalent"
            )

        user = request.user
        try:
            social_tokens = SocialToken.objects.filter(account__user_id=user.id)
        except SocialToken.DoesNotExist:
            return get_response(request)

        for social_token in social_tokens:
            provider = getattr(social_token.account, 'provider', None)
            if provider != 'gitlab':
                continue

            expires_at = getattr(social_token, 'expires_at', None)
            if expires_at and expires_at > timezone.now():
                continue

            try:
                logger.info("Attempting to refresh expired GitLab access_token")
                social_app = SocialApp.objects.get(provider='gitlab')
                gl_client_id = social_app.client_id
                gl_secret = social_app.secret
                gl_refresh_token = social_token.token_secret
                token_url = '{gitlab_url}/oauth/token'.format(gitlab_url=gitlab_url)
                data = {
                    'grant_type': 'refresh_token',
                    'refresh_token': gl_refresh_token,
                    'client_id': gl_client_id,
                    'client_secret': gl_secret,
                }
                response = requests.post(token_url, data=data)
                if response.status_code != 200:
                    logger.error("Failed to refresh expired access_token")
                    logout(request)
                    return get_response(request)
                response_json = json.loads(response.content)
                gl_access_token = response_json['access_token']
                gl_refresh_token = response_json.get('refresh_token', social_token.token_secret)
                expires_in = response_json.get('expires_in', 3600)
                new_expiration_time = timezone.now() + timezone.timedelta(seconds=expires_in)
                social_token.expires_at = new_expiration_time
                social_token.token = gl_access_token
                social_token.token_secret = gl_refresh_token
                social_token.save()

                gitlab_client = gitlab.Gitlab(
                    url=gitlab_url,
                    oauth_token=gl_access_token
                )
                gitlab_client.auth()
            except Exception:
                logger.exception("Failed to refresh expired access_token")
                logout(request)
                return get_response(request)

        return get_response(request)
    return middleware

# ^_^ 