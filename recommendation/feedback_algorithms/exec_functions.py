# -*- coding:utf-8 -*-

"""
helperから呼ばれる各オブジェクト実行用の関数
"""
import relevant_feedback as r_f
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
    init_obj.init_user_model(user_id)

"""
relevant
"""
def get_song_by_relevant(user, emotion):
    r_obj = get_r_obj(user, emotion)
    return get_top_song(r_obj)

def learning_by_relevant(r_obj, l_rate, beta):
    r_obj.set_learning_params(l_rate, beta)
    r_obj.fit()

def learning_and_get_song_by_relevant(user, emotion, l_rate = 0.005, beta = 0.02):
    r_obj = get_r_obj(user, emotion)
    learning_by_relevant(r_obj, l_rate, beta)
    return get_top_song(r_obj)

def get_r_obj(user, emotion):
    return r_f.RelevantFeedback(user, emotion)

def get_top_song(r_obj):
    top_k_songs = r_obj.get_top_k_songs()
    song_ids = [song[1] for song in top_k_songs]
    return song_ids
  
