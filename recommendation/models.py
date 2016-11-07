# -*- coding:utf-8 -*-
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
    cluster = models.ForeignKey(Cluster, null=True, blank=True)

class RecommendSong(models.Model):
    user = models.ForeignKey(User)
    song = models.ForeignKey(Song)

class LikeSong(models.Model):
    user = models.ForeignKey(User)
    song = models.ForeignKey(Song)
    recommend_type = models.IntegerField(null=False, blank=False)

"""
comparison: どちらの曲が良かったか(0: 10曲推薦, 1: インタラクション)
interaction_rate: インタラクションの評価
recommend_rate: 10曲推薦の評価
sung_nums: 知っていた曲の数
compare_method: どちらの推薦が良かったか
free_content: フリー回答
"""
class Questionnaire(models.Model):
    user = models.ForeignKey(User)
    comparison = models.IntegerField(null=False, blank=False)
    interaction_rate = models.IntegerField(null=False, blank=False)
    recommend_rate = models.IntegerField(null=False, blank=False)
    song_nums = models.IntegerField(null=False, blank=False)
    compare_method = models.IntegerField(null=False, blank=False)
    free_content = models.CharField(max_length=255, null=True, blank=True)

"""
印象語検索における適合フィードバックの結果格納
relevant_type: {1: "好き", -1: "嫌い"}
"""
class EmotionRelevantSong(models.Model):
    user = models.ForeignKey(User)
    song = models.ForeignKey(Song)
    relevant_type = models.IntegerField(null=False, blank=False)

class EmotionEmotionbasedSong(models.Model):
    user = models.ForeignKey(User)
    song = models.ForeignKey(Song)
    situation = models.IntegerField(null=False, blank=False)
    #emotion = models.ForeignKey(Cluster)
    feedback_type = models.IntegerField(null=False, blank=False)

class SituationEmotion(models.Model):
    user = models.ForeignKey(User)
    situation = models.IntegerField(null=False, blank=False)
    emotion = models.ForeignKey(Cluster)
