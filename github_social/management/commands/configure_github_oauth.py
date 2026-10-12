import os

from allauth.socialaccount.models import SocialApp
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Configure the GitHub OAuth SocialApp for this Django site."

    def handle(self, *args, **options):
        client_id = os.getenv("GITHUB_CLIENT_ID")
        client_secret = os.getenv("GITHUB_CLIENT_SECRET")
        site_domain = os.getenv("SITE_DOMAIN", "localhost:8000")

        if not client_id or not client_secret:
            raise CommandError(
                "Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET before running "
                "this command."
            )

        site = Site.objects.get(pk=settings.SITE_ID)
        site.domain = site_domain
        site.name = site_domain
        site.save(update_fields=["domain", "name"])

        social_app, created = SocialApp.objects.update_or_create(
            provider="github",
            defaults={
                "name": "GitHub",
                "client_id": client_id,
                "secret": client_secret,
            },
        )
        social_app.sites.set([site])

        action = "Created" if created else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} GitHub OAuth app for {site_domain}. "
                "Callback URL: "
                f"http://{site_domain}/accounts/github/login/callback/"
            )
        )
