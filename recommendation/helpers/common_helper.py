# -*- coding:utf-8 -*-
from recommendation.models import *
import redis
import numpy as np
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from itertools import chain
import random
from recommendation.feedback_algorithms import exec_functions
from datetime import datetime

"""
def get_feedback_dict():

    feedbacks = ["calm", "tense", "aggressive", "lively", "peaceful"]
    feedback_dict = {}
    for i in xrange(2):
        for index, feedback in enumerate(feedbacks):
            key = i * 5 + index
            feedback_dict[key] = feedback

    return feedback_dict
"""

"""
状況に対する印象語選択肢の辞書
"""
def get_search_emotions_dict():
    emotions = {}
    tags = Tag.objects.all()
    for tag in tags:
        if tag.search_flag:
            emotions[tag.id] = (tag.name, tag.japanese)

    return emotions

def init_user_model(user_id, relevant_type):
    """
    ユーザーのモデル初期化
    """
    delete_user_listening_history(user_id, relevant_type)
    exec_functions.init_redis_user_model(str(user_id), relevant_type)

def init_all_user_model(user_id):
    exec_functions.init_redis_user_model(user_id, "emotion")
    exec_functions.init_redis_user_model(user_id, "relevant")

def get_count_listening(user_id, situation, feedback_type):
    """
    ユーザーのそのシチュエーションにおける指定した状況の視聴回数を表示する
    """
    listening_count = 0
    if feedback_type == "relevant":
        listening_count = EmotionRelevantSong.objects.filter(user_id=user_id, situation=situation).values("song").distinct().count()
    else:
        listening_count = EmotionEmotionbasedSong.objects.filter(user_id=user_id, situation=situation).values("song").distinct().count()

    return listening_count

def save_situation_and_emotion(user_id, situation, emotions):
    """
    状況と選択した印象語の永続化完了
    """
    for emotion in emotions:
        obj, created = SituationEmotion.objects.get_or_create(user_id=user_id, situation=situation, emotion_id=int(emotion))

def get_now_search_situation(user_id):
    """
    現在のユーザーの検索状況を取得する(emotion一つのみ取得)
    """
    user_situations = SituationEmotion.objects.filter(user_id=user_id).values()
    situation_count = len(user_situations)
    now_situation = user_situations[situation_count-1]['situation']
    emotions = []
    #emotions = [user_situations[situation_count-1]["emotion_id"]]
    for i in xrange(situation_count-1, 0, -1):
        if user_situations[i]["situation"] != now_situation:
            break
        emotions.append(user_situations[i]["emotion_id"])
    return now_situation, emotions

def delete_user_listening_history(user_id, relevant_type):
    if relevant_type == "relevant":
        EmotionRelevantSong.objects.filter(user_id=user_id).delete()
    else:
        EmotionEmotionbasedSong.objects.filter(user_id=user_id).delete()

def search_by_emotion(emotion):
    """
    印象語による検索
    """
    emotion_map = {1: "-pop", 2: "-ballad", 3: "-rock"}
    songs = SearchMusicCluster.objects.order_by(emotion_map[emotion])
    return songs[:300]

def get_song_objs(song_ids):
    """
    楽曲ID集合からSong Object取得
    """
    song_objs = Song.objects.filter(id__in=song_ids)
    return song_objs

def get_song_obj(song_id):
    """
    楽曲IDからSong Object取得
    """
    song_obj = Song.objects.filter(id=song_id)
    return song_obj

def save_search_song(user_id, song_id, situation, feedback_type):
    """
    推薦した楽曲を保存する
    feedback_type: {0: 適合性, 1: 印象語}
    """
    now = datetime.now()
    if SearchSong.objects.filter(user_id=user_id, situation=situation, song_id=song_id, feedback_type=feedback_type).exists():
        SearchSong.objects.filter(user_id=user_id, situation=situation, song_id=song_id, feedback_type=feedback_type).update(updated_at=now)
    else:
        SearchSong.objects.create(user_id=user_id, song_id=song_id, situation=situation, feedback_type=feedback_type, created_at=now, updated_at=now)

def get_now_search_song(user_id, situation, feedback_type):
    
    now_song_obj = SearchSong.objects.order_by("updated_at").filter(user_id=user_id, situation=situation, feedback_type=feedback_type).reverse().first()
    return get_song_obj(now_song_obj.id)

def is_back_song(user_id, situation, song_id, feedback_type):
    """
    この楽曲より前の楽曲が存在するか
    """
    song_obj = SearchSong.objects.filter(user_id=user_id, situation=situation, song_id=song_id, feedback_type=feedback_type)
    if song_obj:
        is_back_song = SearchSong.objects.filter(user_id=user_id, situation=situation, created_at__lt=song_obj[0].created_at).exists()
    else:
        is_back_song = False
    return is_back_song

def get_top_song(user, situation, emotions, feedback_type):
    """
    モデルから楽曲取得
    """
    song_obj = None
    if SearchSong.objects.filter(user_id=user, situation=situation, feedback_type=feedback_type).exists():
        song_obj = get_now_search_song(user, situation, feedback_type)
    else:
        song_ids = exec_functions.get_song_by_relevant(user, emotions)
        song_obj = get_song_objs(song_ids)
        save_search_song(user, song_obj[0].id, situation, feedback_type)
    return song_obj

def get_search_songs(user_id, situation, feedback_type):
    """
    検索された楽曲の一覧を取得する
    """
    search_song_objs = SearchSong.objects.filter(user_id=user_id, situation=situation, feedback_type=feedback_type)
    return search_song_objs

def save_best_song(user_id, song_id, situation, feedback_type):
    """
    ベスト楽曲の永続化
    """
    obj, created = SearchBestSong.objects.get_or_create(user_id=user_id, song_id=song_id, situation=situation, search_type=feedback_type)

def save_last_song(user_id, situation, feedback_type):
    """
    最後に視聴した楽曲を取得して永続化する
    """
    last_song_id = get_last_song(user_id, situation, feedback_type)
    obj, created = SearchLastSong.objects.get_or_create(user_id=user_id, song_id=last_song_id, situation=situation, search_type=feedback_type)

def get_last_song(user_id, situation, feedback_type):
    """
    user_id, situation, feedback_typeにおける最後に視聴した楽曲を取得する
    """
    last_song_id = SearchSong.objects.filter(user_id=user_id, situation=situation, feedback_type=feedback_type).order_by("updated_at").reverse()[0].song_id
    return last_song_id

def get_not_feedback_type(user_id, situation):
    """
    ユーザーがその状況で行っていないフィードバックタイプを返す
    @return(feedback_type): route
    """
    s_b_obj = SearchBestSong.objects.filter(user_id=user_id, situation=situation)
    if len(s_b_obj) == 2:
        return ""
    else:
        if s_b_obj[0].search_type == 0:
            return "emotion_feedback_single/"
        else:
            return "relevant_feedback_single/"
