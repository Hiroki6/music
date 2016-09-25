# -*- coding:utf-8 -*-
"""
印象語検索システムに関するhelper関数
"""
from recommendation.models import Song, Artist, Preference, RecommendSong, LikeSong, Questionnaire, MusicCluster
import redis
import numpy as np
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from itertools import chain
import random

"""
印象語による検索
"""
def search_by_emotion(emotion):
    emotion_map = {1: "-calm", 2: "-tense", 3: "-aggressive", 4: "-lively", 5: "-peaceful"}
    songs = MusicCluster.objects.order_by(emotion_map[emotion])
    return songs[:300]

def get_random_k_songs(k, song_obj):
    k_song_objs = []
    for i in xrange(k):
        index = random.randint(0, len(song_obj)-1)
        k_song_objs.append(song_obj[index])
    return k_song_objs
