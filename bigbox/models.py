from django.db import models
from django.contrib.auth.models import User
from datetime import datetime


class CloudInterface(models.Model):
    name = models.CharField(max_length=20, db_index=True)
    display_name = models.CharField(max_length=30)
    icon = models.CharField(max_length=30)
    class_name = models.CharField(max_length=30)


class StorageAccount(models.Model):
    user = models.ForeignKey(User, db_index=True)
    cloud = models.ForeignKey(CloudInterface)
    identifier = models.TextField()
    status = models.IntegerField()
    refresh_token = models.TextField(blank=True)
    refresh_token_expire = models.DateTimeField(null=True, blank=True)
    access_token = models.TextField(blank=True)
    access_token_expire = models.DateTimeField(null=True, blank=True)
    additional_data = models.TextField(blank=True)
