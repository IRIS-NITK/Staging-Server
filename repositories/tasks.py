"""Celery task discovery for the repositories application."""

from repositories.services import create

__all__ = ["create"]
