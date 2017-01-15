# -*- coding:utf-8 -*-

"""
helperから呼ばれる各オブジェクト実行用の関数
"""
import relevant_feedback as r_f
import emotion_feedback as e_f
import init_search as i_s
import init_redis

def init_redis_all_model(feedback_type):
    """
    すべて初期化
    """
    init_obj = init_redis.InitRedis(feedback_type = feedback_type)
    init_obj.init_all_user_model()

def init_redis_user_model(user_id, feedback_type):
    """
    特定のユーザーだけ初期化
    """
    init_obj = init_redis.InitRedis(feedback_type = feedback_type)
    init_obj.update_user_model(user_id)

def get_song_by_relevant(user, situation, emotion):
    """
    relevant
    """         
    r_obj = get_r_obj(user, situation, emotion)
    #return get_init_songs(r_obj)
    return get_top_song_by_relevance(r_obj)

def learning_by_relevant(r_obj, l_rate, beta):
    r_obj.set_learning_params(l_rate, beta, "batch")
    r_obj.fit()

def learning_and_get_song_by_relevant(user, situation, emotion, l_rate = 0.005, beta = 0.02):
    r_obj = get_r_obj(user, situation, emotion)
    learning_by_relevant(r_obj, l_rate, beta)
    return get_top_song_by_relevance(r_obj)

def get_r_obj(user, situation, emotion):
    return r_f.RelevantFeedback(user, situation, emotion)

def get_song_by_emotion(user, emotions, situation):
    """
    emotion
    """
    e_obj = get_e_obj(user, emotions, situation)
    #return get_init_songs(e_obj)
    return get_top_song_by_emotion(e_obj)

def learning_by_emotion(e_obj):
    e_obj.set_params()
    e_obj.fit()

def learning_and_get_song_by_emotion(user, emotions, situation, is_k_ranking = False):
    e_obj = get_e_obj(user, emotions, situation)
    if is_k_ranking:
        learning_by_emotion_rankings(e_obj)
    else:
        learning_by_emotion(e_obj)
    return get_top_song_by_emotion(e_obj)

def get_e_obj(user, emotions, situation):
    return e_f.EmotionFeedback(user, emotions, situation)

def learning_by_emotion_rankings(e_obj):
    e_obj.set_params_k_rankings()
    e_obj.k_batch_fit()

"""
印象語フィードバックの楽曲取得
"""
def get_top_song_by_emotion(obj):
    top_k_songs = obj.get_top_k_songs()
    song_ids = [song[1] for song in top_k_songs]
    return song_ids

"""
適合性フィードバックの楽曲取得
"""
def get_top_song_by_relevance(obj):
    top_k_songs = obj.get_top_k_songs()
    song_ids = [song[1] for song in top_k_songs]
    return song_ids

"""
初期検索の楽曲取得
適合性、印象語の両方で使用
"""
def get_init_songs(obj):
    init_songs = obj.get_init_songs()
    return init_songs

"""
baselineの実装
"""
def get_top_song_by_baseline(user, emotion):
    e_obj = e_f.EmotionBaseline(user, emotion)
    e_obj.set_params()
    top_song = e_obj.get_top_song()
    return [top_song]

"""
各状況の最初の検索
"""
def get_init_search_songs(user, situation, emotions):
    i_obj = i_s.InitSearch(user, situation, emotions)
    top_k_songs = i_obj.get_top_k_songs()
    return top_k_songs

if __name__ == "__main__":
    # DB初期化
    init_redis_all_model("emotion")
    init_redis_all_model("relevant")
