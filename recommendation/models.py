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

class MusicCluster(models.Model):
    song = models.ForeignKey(Song)
    aggressive = models.FloatField(null=True, blank=True)
    calm = models.FloatField(null=True, blank=True)
    lively = models.FloatField(null=True, blank=True)
    peaceful = models.FloatField(null=True, blank=True)
    tense = models.FloatField(null=True, blank=True)

class SongTag(models.Model):
    song = models.ForeignKey(Song)
    aggressive = models.FloatField(null=True, blank=True)
    ambitious = models.FloatField(null=True, blank=True)
    angry = models.FloatField(null=True, blank=True)
    anxious = models.FloatField(null=True, blank=True)
    bright = models.FloatField(null=True, blank=True)
    calm = models.FloatField(null=True, blank=True)
    carefree = models.FloatField(null=True, blank=True)
    cheerful = models.FloatField(null=True, blank=True)
    cold = models.FloatField(null=True, blank=True)
    complex = models.FloatField(null=True, blank=True)
    confident = models.FloatField(null=True, blank=True)
    detached = models.FloatField(null=True, blank=True)
    difficult = models.FloatField(null=True, blank=True)
    elegant = models.FloatField(null=True, blank=True)
    fun = models.FloatField(null=True, blank=True)
    gentle = models.FloatField(null=True, blank=True)
    happy = models.FloatField(null=True, blank=True)
    harsh = models.FloatField(null=True, blank=True)
    hopeful = models.FloatField(null=True, blank=True)
    hostile = models.FloatField(null=True, blank=True)
    hungry = models.FloatField(null=True, blank=True)
    innocent = models.FloatField(null=True, blank=True)
    intimate = models.FloatField(null=True, blank=True)
    lazy = models.FloatField(null=True, blank=True)
    lively = models.FloatField(null=True, blank=True)
    messy = models.FloatField(null=True, blank=True)
    party = models.FloatField(null=True, blank=True)
    peaceful = models.FloatField(null=True, blank=True)
    relaxed = models.FloatField(null=True, blank=True)
    reserved = models.FloatField(null=True, blank=True)
    reverent = models.FloatField(null=True, blank=True)
    romantic = models.FloatField(null=True, blank=True)
    sad = models.FloatField(null=True, blank=True)
    sexy = models.FloatField(null=True, blank=True)
    silly = models.FloatField(null=True, blank=True)
    smooth = models.FloatField(null=True, blank=True)
    soft = models.FloatField(null=True, blank=True)
    sweet = models.FloatField(null=True, blank=True)
    tender = models.FloatField(null=True, blank=True)
    tense = models.FloatField(null=True, blank=True)
    thoughtful = models.FloatField(null=True, blank=True)
    warm = models.FloatField(null=True, blank=True)
    weary = models.FloatField(null=True, blank=True)

