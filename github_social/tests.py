from django.test import TestCase, RequestFactory
from django.utils import timezone
from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken
from django.contrib.auth import get_user_model

from stagingserver.middleware import oauth_session_enforcement


class OAuthMiddlewareGitHubTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = get_user_model().objects.create_user(username='gh-user', password='pw')
        self.social_app = SocialApp.objects.create(
            provider='github',
            name='GitHub',
            client_id='client-id',
            secret='secret',
        )
        self.social_account = SocialAccount.objects.create(
            user=self.user,
            provider='github',
            uid='123',
            extra_data={},
        )
        self.social_token = SocialToken.objects.create(
            account=self.social_account,
            app=self.social_app,
            token='gh-token',
            token_secret='gh-secret',
            expires_at=timezone.now() + timezone.timedelta(hours=1),
        )

    def test_github_token_is_ignored_by_gitlab_refresh_middleware(self):
        request = self.factory.get('/github_social/')
        request.user = self.user

        def next_view(request):
            return 'ok'

        wrapped = oauth_session_enforcement(next_view)
        response = wrapped(request)

        self.assertEqual(response, 'ok')
