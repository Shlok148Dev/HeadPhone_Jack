"""Accounts (Tech Bible 3.1). Sprint 0 skeleton; backend-engineer extends in S1."""

import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class TimeStamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class User(AbstractUser, TimeStamped):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=60, blank=True)
    birth_year = models.PositiveSmallIntegerField(null=True, blank=True)
    college = models.CharField(max_length=120, blank=True)
    city = models.CharField(max_length=80, blank=True)
    discoverable = models.BooleanField(default=False)
    private_until = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "users"
