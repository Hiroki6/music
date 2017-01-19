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
from datetime import datetime
from common_helper import *


"""
適合性フィードバックの内容永続化
"""
def save_user_song(user_id, song_id, relevant_type, situation):

    now = datetime.now()
    if EmotionRelevantSong.objects.filter(user_id=user_id, situation=situation, song_id=song_id).exists():
        EmotionRelevantSong.objects.filter(user_id=user_id, situation=situation, song_id=song_id).update(updated_at=now, relevant_type=relevant_type)
    else:
        EmotionRelevantSong.objects.create(user_id=user_id, song_id=song_id, situation=situation, relevant_type=relevant_type, created_at=now, updated_at=now)

"""
学習と楽曲の取得(relevant)
"""
def learning_and_get_song(user, situation):
    song_ids = exec_functions.learning_and_get_song_by_relevant(user, situation)
    return get_song_objs(song_ids)

"""
トップの楽曲取得
"""
def get_top_song(user, situation, feedback_type):
    song_obj = None
    # if SearchSong.objects.filter(user_id=user, situation=situation, feedback_type=feedback_type).exists():
    #     song_obj = get_now_search_song(user, situation, feedback_type)
    # else:
    song_ids = exec_functions.get_song_by_relevant(user, situation)
    song_obj = get_song_objs(song_ids)
    save_search_song(user, song_obj[0].id, situation, feedback_type)
    return song_obj

"""
一つ前の楽曲取得
すでに楽曲がEmotionRelevantSongに含まれていたら、objectを走査する
含まれていない場合、最新のsong_objを取得する
"""
def get_back_song(user, song_id, situation):
    back_song_id = 0
    if EmotionRelevantSong.objects.filter(user_id=user, situation=situation, song_id=song_id).exists():
        all_songs_by_situation = EmotionRelevantSong.objects.order_by("updated_at").filter(user_id=user, situation=situation).values().reverse()
        for index, song_obj in enumerate(all_songs_by_situation):
            if song_obj["song_id"] == song_id:
                back_song_id = all_songs_by_situation[index+1]["song_id"]
                break
    else:
        back_song_id = EmotionRelevantSong.objects.order_by("id").filter(user_id=user, situation=situation).values().reverse()[0]["song_id"]
    if back_song_id:
        SearchSong.objects.filter(user_id=user, situation=situation, song_id=back_song_id, feedback_type=0).update(updated_at=datetime.now())
    return get_song_obj(back_song_id)

def get_last_top_songs(user):
    """
    終了後のtop_kの楽曲オブジェクトを取得する
    """
    r = get_redis_obj("localhost", 6379, 2)
    song_ids = get_one_dim_params(r, "top_k_songs_" + str(user))
    song_objs = []
    for index, song_id in enumerate(song_ids):
        song_objs.append((index+1, Song.objects.filter(id=song_id)[0]))
    return song_objs

