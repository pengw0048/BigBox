from django.db import models
from django.contrib.auth.models import User


class CloudInterface(models.Model):
    name = models.CharField(max_length=20, primary_key=True)
    display_name = models.CharField(max_length=30)
    icon = models.CharField(max_length=30)
    class_name = models.CharField(max_length=30)


class StorageAccount(models.Model):
    user = models.ForeignKey(User, db_index=True)
    cloud = models.ForeignKey(CloudInterface)
    identifier = models.TextField()
    status = models.IntegerField()
    refresh_token = models.TextField()
    refresh_token_expire = models.DateTimeField()
    access_token = models.TextField()
    access_token_expire = models.DateTimeField()
    additional_data = models.TextField()
