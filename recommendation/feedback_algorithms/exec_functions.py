# -*- coding:utf-8 -*-

"""
helperから呼ばれる各オブジェクト実行用の関数
"""
import relevant_feedback as r_f
import emotion_feedback as e_f
import init_redis

"""
すべて初期化
"""
def init_redis_all_model(feedback_type):

    init_obj = init_redis.InitRedis(feedback_type = feedback_type)
    init_obj.init_all_user_model()

"""
特定のユーザーだけ初期化
"""
def init_redis_user_model(user_id, feedback_type):

    init_obj = init_redis.InitRedis(feedback_type = feedback_type)
    init_obj.update_user_model(user_id)

"""
relevant
"""
def get_song_by_relevant(user, emotion):
    r_obj = get_r_obj(user, emotion)
    return get_top_song(r_obj)

def learning_by_relevant(r_obj, l_rate, beta):
    r_obj.set_learning_params(l_rate, beta, "batch")
    r_obj.fit()

def learning_and_get_song_by_relevant(user, emotion, l_rate = 0.005, beta = 0.02):
    r_obj = get_r_obj(user, emotion)
    learning_by_relevant(r_obj, l_rate, beta)
    return get_top_song(r_obj)

def get_r_obj(user, emotion):
    return r_f.RelevantFeedback(user, emotion)

"""
emotion
"""
def get_song_by_emotion(user, emotions):
    e_obj = get_e_obj(user, emotions)
    return get_top_song(e_obj)

def learning_by_emotion(e_obj):
    e_obj.set_params()
    e_obj.fit()

def learning_and_get_song_by_emotion(user, emotions, is_k_ranking = False):
    e_obj = get_e_obj(user, emotions)
    if is_k_ranking:
        learning_by_emotion_rankings(e_obj)
    else:
        learning_by_emotion(e_obj)
    return get_top_song(e_obj)

def get_e_obj(user, emotions):
    return e_f.EmotionFeedback(user, emotions)

def learning_by_emotion_rankings(e_obj):
    e_obj.set_params_k_rankings()
    e_obj.k_fit()

"""
共通
"""
def get_top_song(obj):
    top_k_songs = obj.get_top_k_songs()
    song_ids = [song[1] for song in top_k_songs]
    return song_ids

"""
baselineの実装
"""
def get_top_song_by_baseline(user, emotion):
    e_obj = e_f.EmotionBaseline(user, emotion)
    e_obj.set_params()
    top_song = e_obj.get_top_song()
    return [top_song]
