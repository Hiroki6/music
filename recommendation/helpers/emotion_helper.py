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

"""
適合性フィードバックの内容永続化
"""
def save_user_relevant_song(user_id, song_id, relevant_type):

    obj, created = EmotionRelevantSong.objects.get_or_create(user_id=user_id, song_id=song_id, relevant_type=relevant_type)

def save_user_emotion_song(user_id, song_id, situation, feedback_type):

    obj, created = EmotionEmotionbasedSong.objects.get_or_create(user_id=user_id, song_id=song_id, situation=situation, feedback_type=feedback_type)


"""
状況と選択した印象語の永続化完了
"""
def save_situation_and_emotion(user_id, situation, emotions):

    for emotion in emotions:
        obj, created = SituationEmotion.objects.get_or_create(user_id=user_id, situation=situation, emotion_id=int(emotion))

"""
モデルから楽曲取得(relevant)
"""
def get_top_song_relevant(user, emotion):
    song_ids = exec_functions.get_song_by_relevant(user, emotion)
    return get_song_objs(song_ids)

"""
モデルから楽曲取得(emotion)
"""
def get_top_song_emotion(user, emotions):
    song_ids = exec_functions.get_song_by_emotion(user, emotions)
    return get_song_objs(song_ids)

"""
学習と楽曲の取得(emotion)
"""
def learning_and_get_song_by_emotion(user, emotions):
    song_ids = exec_functions.learning_and_get_song_by_emotion(user, emotions, True)
    return get_song_objs(song_ids)

"""
学習と楽曲の取得(relevant)
"""
def learning_and_get_song_by_relevant(user, emotion):
    song_ids = exec_functions.learning_and_get_song_by_relevant(user, emotion)
    return get_song_objs(song_ids)

"""
楽曲ID集合からSong Object取得
"""
def get_song_objs(song_ids):
    song_objs = Song.objects.filter(id__in=song_ids)
    return song_objs

"""
ユーザーのモデル初期化
"""
def init_user_model(user_id, relevant_type):
    delete_user_listening_history(user_id, relevant_type)
    exec_functions.init_redis_user_model(str(user_id), relevant_type)

def init_all_user_model(user_id):
    exec_functions.init_redis_user_model(user_id, "emotion")
    exec_functions.init_redis_user_model(user_id, "relevant")

def delete_user_listening_history(user_id, relevant_type):
    if relevant_type == "relevant":
        EmotionRelevantSong.objects.filter(user_id=user_id).delete()
    else:
        EmotionEmotionbasedSong.objects.filter(user_id=user_id).delete()

"""
現在のユーザーの検索状況を取得する
"""
def get_now_search_situation(user_id):

    user_situations = SituationEmotion.objects.filter(user_id=user_id).values()
    situation_count = len(user_situations)
    now_situation = user_situations[situation_count-1]['situation']
    emotions = []
    for i in xrange(situation_count-1, 0, -1):
        if user_situations[i]["situation"] != now_situation:
            break
        emotions.append(user_situations[i]["emotion_id"])
    return now_situation, emotions

def save_experiment(song_id, evaluation):

    obj, created = Experiment.objects.get_or_create(song_id=song_id, evaluation=evaluation)
