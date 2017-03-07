from django.db import models
from django.contrib.auth.models import User


class CloudInterface(models.Model):
    name = models.CharField(max_length=20, db_index=True)
    display_name = models.CharField(max_length=30)
    icon = models.CharField(max_length=30)
    class_name = models.CharField(max_length=30)

    def __str__(self):
        return str(self.name) + ' ' + str(self.display_name) + ' ' + str(self.icon) + ' ' + str(self.class_name)


class StorageAccount(models.Model):
    user = models.ForeignKey(User, db_index=True)
    cloud = models.ForeignKey(CloudInterface)
    identifier = models.TextField()
    status = models.IntegerField()
    credentials = models.TextField(blank=True)
    user_full_name = models.TextField()
    user_short_name = models.TextField()
    email = models.TextField()
    display_name = models.TextField()
    color = models.CharField(max_length=8)

    def __str__(self):
        return ' '.join([str(self.user), str(self.cloud), str(self.identifier), str(self.status),
                         str(self.user_full_name), str(self.user_short_name), str(self.email), str(self.display_name),
                         str(self.color)])

    def save(self, *args, **kwargs):
        if not self.user_short_name:
            self.user_short_name = self.user_full_name.split(' ')[0]
        if not self.display_name:
            self.display_name = "%s's %s" % (self.user_short_name, self.cloud.display_name)
        super().save(*args, **kwargs)
