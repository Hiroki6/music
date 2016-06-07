from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User

# Create your models here.
# class User(models.Model):
#     name = models.CharField(max_length=50)
#     email = models.CharField(max_length=50)

class Cluster(models.Model):
    name = models.CharField(max_length=50)

class Tag(models.Model):
    name = models.CharField(max_length=50)
    cluster = models.ForeignKey(Cluster, null=True)

class Artist(models.Model):
    name = models.CharField(max_length=255)

class Song(models.Model):
    artist = models.ForeignKey(Artist)
    name = models.CharField(max_length=255)
    url = models.CharField(max_length=255, null=True)

class Preference(models.Model):
    user = models.ForeignKey(User)
    song = models.ForeignKey(Song)
