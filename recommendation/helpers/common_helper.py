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
def get_search_emotions_map():
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

def get_init_flag(user_id, situation, feedback_type):
    """
    フィードバックを一回以上行っているかどうか
    """
    if feedback_type == "relevant":
        listening_count = EmotionRelevantSong.objects.filter(user_id=user_id, situation=situation).values("song").exclude(relevant_type=0).distinct().count()
    else:
        listening_count = EmotionEmotionbasedSong.objects.filter(user_id=user_id, situation=situation).values("song").exclude(feedback_type=7).distinct().count()
    return listening_count == 0

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
    for i in xrange(situation_count-1, -1, -1):
        if user_situations[i]["situation"] == now_situation:
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


def save_search_song_both_type(user_id, song_id, situation):
    """
    推薦した楽曲を永続化する（両方の検索タイプ）
    """
    now = datetime.now()
    for feedback_type in xrange(2):
        SearchSong.objects.get_or_create(user_id=user_id, song_id=song_id, situation=situation, feedback_type=feedback_type, created_at=now, updated_at=now)

def get_now_search_songs(user_id, situation, feedback_type):
    
    now_song_obj = SearchSong.objects.order_by("updated_at").filter(user_id=user_id, situation=situation, feedback_type=feedback_type).reverse().first()
    return get_song_obj(now_song_obj.song_id)

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
    sb_obj = SearchLastSong.objects.filter(user_id=user_id, situation=situation)
    if len(sb_obj) >= 2:
        return 2
    else:
        return sb_obj[0].search_type

def get_answer_song(user_id, type):
    """
    各状況のベストソング辞書取得
    {situation: [song_obj]}
    """
    if type == "best":
        s_objs = SearchBestSong.objects.filter(user_id=user_id)
    else:
        s_objs = SearchLastSong.objects.filter(user_id=user_id)
    song_map = {}
    for s_obj in s_objs:
        situation = s_obj.situation
        if not song_map.has_key(situation):
            song_map.setdefault(situation, [])
        song_map[situation].append(s_obj)
    
    return song_map

def get_answers_song(user_id):
    """
    ベスト楽曲、ラスト楽曲の両方の取得
    ({situation: [best_song_obj]}, {situation: [last_song_obj]})
    """
    best_song_map = get_answer_song(user_id, "best")
    last_song_map = get_answer_song(user_id, "last")

    return best_song_map, last_song_map

def get_listening_songs_by_situation(user_id, situation):
    #song_ids = SearchSong.objects.values_list('song_id', flat=True).order_by("song_id").filter(user_id=user_id, situation=situation).distinct()
    song_objs = SearchSong.objects.filter(user_id=user_id, situation=situation).distinct()
    #song_objs = SearchSong.objects.filter(song_id__in=song_ids)
    return song_objs[1:]

def save_best_songs(user_id, situation, song_ids, feedback_types):
    
    for song_id, feedback_type in zip(song_ids, feedback_types):

        obj, created = SearchBestSong.objects.get_or_create(user_id=user_id, song_id=song_id, situation=situation, search_type=feedback_type)

def get_url_about_search(user_id):
    """
    検索終了かどうかの判定
    終了ならアンケート画面
    終了でなければ検索画面へ
    """
    searched_situations = SearchBestSong.objects.filter(user_id=user_id).values_list('situation', flat=True).order_by('situation').distinct()
    if len(searched_situations) >= 2:
        return "/recommendation/emotion_questionnaire/"
    else:
        return "/recommendation/"

def get_searched_situations_by_user(user_id):
    """
    ユーザーが既に検索している状況を削除する
    """
    user_all_situations = SituationEmotion.objects.filter(user_id=user_id).values_list("situation", flat=True).order_by("situation").distinct()
    return user_all_situations

def get_situations_map(user_id): 
    situations = {1: "運動中", 2: "起床時", 3: "作業中", 4: "通学中", 5: "就寝時", 6: "運転中"}
    user_searched_situations = get_searched_situations_by_user(user_id)
    for situation in user_searched_situations:
        situations.pop(situation)

    return situations

def save_emotion_questionnaire(user_id, relevant_rate, emotion_rate, comparison):
    
    obj, created = EvaluateSearch.objects.get_or_create(user_id=user_id, search_type="relevant", rating=relevant_rate)
    obj, created = EvaluateSearch.objects.get_or_create(user_id=user_id, search_type="emotion", rating=emotion_rate)
    if comparison:
        obj, created = ComparisonSearchType.objects.get_or_create(user_id=user_id, search_type="emotion")
    else:
        obj, created = ComparisonSearchType.objects.get_or_create(user_id=user_id, search_type="relevant")

def get_redis_obj(host, port, db):
    """
    redisオブジェクトを取得
    """
    return redis.Redis(host=host, port=port, db=db)

def get_one_dim_params(redis_obj, key):
    """
    redisから一次元配列の取得
    """
    params = redis_obj.lrange(key, 0, -1)
    params = np.array(params, dtype=np.int64)
    return params

def save_rank_songs(user_id, situation, song_ids, ranks, feedback_type):
    
    for song_id, rank in zip(song_ids, ranks):
        obj, created = TopKRelevantSong.objects.get_or_create(user_id=user_id, song_id=song_id, situation=situation, search_type=feedback_type, song_rank=rank)

def get_init_search_songs(user, situation):
    song_ids = exec_functions.get_init_search_songs(user, situation)
    song_objs = []
    for index, song_id in enumerate(song_ids):
        song_objs.append((index+1, Song.objects.filter(id=song_id)[0]))
    return song_objs

def get_next_song(user, situation, listening_count, feedback_type):
    next_song = exec_functions.get_next_song(user, situation, listening_count)
    save_search_song(user, next_song, situation, feedback_type)
    song_obj = Song.objects.filter(id=next_song)
    return song_obj

def save_init_rank_songs(user_id, situation, song_ids, ranks):
    for song_id, rank in zip(song_ids, ranks):
       obj, created = InitTopKRelevantSong.objects.get_or_create(user_id=user_id, song_id=song_id, situation=situation, song_rank=rank)
  
def get_now_situation(user_id):
    """
    現在のユーザーの状況を取得する
    """
    now_situation = Situation.objects.order_by("id").filter(user_id=user_id).last().situation
    return now_situation

def save_situation(user_id, situation):
    """
    状況の永続化完了
    """
    obj, created = Situation.objects.get_or_create(user_id=user_id, situation=situation)

