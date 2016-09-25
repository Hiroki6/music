# -*- coding:utf-8 -*-
"""
印象語検索システムに関するhelper関数
"""
from recommendation.models import *
import redis
import numpy as np
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from itertools import chain
import random
from recommendation.feedback_algorithms import exec_functions


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

def save_user_relevant_song(user_id, song_id, relevant_type):

    obj, created = EmotionRelevantSong.objects.get_or_create(user_id=user_id, song_id=song_id, relevant_type=relevant_type)

def get_top_song_relevant(user, emotion):
    song_id = exec_functions.get_song_by_relevant(user, emotion)
    song_obj = Song.objects.filter(id=song_id)
    return song_obj
