# -*- coding:utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User
from datetime import datetime

# Create your models here.
# class User(models.Model):
#     name = models.CharField(max_length=50)
#     email = models.CharField(max_length=50)

class Cluster(models.Model):
    name = models.CharField(max_length=50)

class Tag(models.Model):
    """
    japanese: 和訳
    """
    name = models.CharField(max_length=50)
    japanese = models.CharField(max_length=50, null=True)
    cluster = models.ForeignKey(Cluster, null=True)
    search_flag = models.BooleanField(default=True)

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

class Questionnaire(models.Model):
    """
    comparison: どちらの曲が良かったか(0: 10曲推薦, 1: インタラクション)
    interaction_rate: インタラクションの評価
    recommend_rate: 10曲推薦の評価
    sung_nums: 知っていた曲の数
    compare_method: どちらの推薦が良かったか
    free_content: フリー回答
    """
    user = models.ForeignKey(User)
    comparison = models.IntegerField(null=False, blank=False)
    interaction_rate = models.IntegerField(null=False, blank=False)
    recommend_rate = models.IntegerField(null=False, blank=False)
    song_nums = models.IntegerField(null=False, blank=False)
    compare_method = models.IntegerField(null=False, blank=False)
    free_content = models.CharField(max_length=255, null=True, blank=True)

class EmotionRelevantSong(models.Model):
    """
    印象語検索における適合フィードバックの結果格納
    relevant_type: {1: "好き", -1: "嫌い"}
    """
    user = models.ForeignKey(User)
    song = models.ForeignKey(Song)
    relevant_type = models.IntegerField(null=False, blank=False)
    situation = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default=datetime.now())
    updated_at = models.DateTimeField(default=datetime.now())

class EmotionEmotionbasedSong(models.Model):
    user = models.ForeignKey(User)
    song = models.ForeignKey(Song)
    situation = models.IntegerField(null=False, blank=False)
    feedback_type = models.IntegerField(null=False, blank=False)
    created_at = models.DateTimeField(default=datetime.now())
    updated_at = models.DateTimeField(default=datetime.now())

class SearchCluster(models.Model):
    """
    印象語検索用のクラスタモデル
    """
    name = models.CharField(max_length=50)

class SituationEmotion(models.Model):
    user = models.ForeignKey(User)
    situation = models.IntegerField(null=False, blank=False)
    emotion = models.ForeignKey(Tag)

class SearchSong(models.Model):
    """
    推薦された楽曲
    feedback_type: {0: 適合性, 1: 印象語}
    """
    user = models.ForeignKey(User)
    song = models.ForeignKey(Song)
    situation = models.IntegerField(null=False, blank=False)
    feedback_type = models.IntegerField(null=False, blank=False)
    created_at = models.DateTimeField(default=datetime.now())
    updated_at = models.DateTimeField(default=datetime.now())

class SearchTag(models.Model):
    """
    タグとクラスタへの所属度
    """
    name = models.CharField(max_length=50)
    pop = models.FloatField(null=True, blank=True)
    ballad = models.FloatField(null=True, blank=True)
    rock = models.FloatField(null=True, blank=True)
    cluster = models.CharField(max_length=50, null=True, blank=True)

class SearchMusicCluster(models.Model):
    """
    楽曲とそれぞれのクラスタの平均値
    """
    song = models.ForeignKey(Song)
    pop = models.FloatField(null=True, blank=True)
    ballad = models.FloatField(null=True, blank=True)
    rock = models.FloatField(null=True, blank=True)
    cluster = models.ForeignKey(SearchCluster, null=True, blank=True)

class SearchBestSong(models.Model):
    """
    ユーザーの状況ごとのベスト楽曲
    """
    user = models.ForeignKey(User)
    song = models.ForeignKey(Song)
    situation = models.IntegerField(null=False, blank=False)
    search_type = models.IntegerField(null=False, blank=False)

class SearchLastSong(models.Model):
    """
    ユーザーの状況ごとで最後に視聴した楽曲
    """
    user = models.ForeignKey(User)
    song = models.ForeignKey(Song)
    situation = models.IntegerField(null=False, blank=False)
    search_type = models.IntegerField(null=False, blank=False)

class ComparisonSong(models.Model):
    """
    search_type: どちらのタイプの楽曲が良かったか
    song_type: 最後の楽曲か一番良かった楽曲か
    """
    user = models.ForeignKey(User)
    search_type = models.CharField(max_length=50)
    song_type = models.CharField(max_length=50)
    situation = models.IntegerField(null=False, blank=False)

class EvaluateSearch(models.Model):
    """
    search_type: 検索タイプ
    rating: 評価値(5段階)
    """
    user = models.ForeignKey(User)
    search_type = models.CharField(max_length=50)
    rating = models.IntegerField(null=False, blank=False)

class ComparisonSearchType(models.Model):
    """
    どちらの検索タイプが良かったか比較する
    """
    user = models.ForeignKey(User)
    search_type = models.CharField(max_length=50)

class TopKRelevantSong(models.Model):
    """
    各検索において最後に提示された１０曲から好きだと言われた楽曲
    """
    user = models.ForeignKey(User)
    search_type = models.CharField(max_length=50)
    song_rank = models.IntegerField(null=False, blank=False)
    song = models.ForeignKey(Song)
    situation = models.IntegerField(null=False, blank=False)
