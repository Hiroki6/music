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
def learning_and_get_song(user, emotion):
    song_ids = exec_functions.learning_and_get_song_by_relevant(user, emotion)
    return get_song_objs(song_ids)

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
