"""Celery task discovery for the main application."""

from main.services import deploy

__all__ = ["deploy"]
