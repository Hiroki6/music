# -*- coding:utf-8 -*-
from .models import Song, Artist, Preference, RecommendSong, LikeSong, Questionnaire
import redis
import numpy as np
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
# そのユーザーの好みの楽曲リスト取得
def get_user_preference(user_id):

    songs = []
    preferences = Preference.objects.filter(user_id=user_id)
    for preference in preferences:
        songs.append(preference.song_id)

    return songs

# ユーザーがまだ聞いていない楽曲のリスト取得
def get_user_not_listening_songs(user_id):

    listening_songs = get_user_preference(user_id)
    songs = Song.objects.exclude(id__in=listening_songs)
    return songs

def get_feedback_dict():

    feedbacks = ["calm", "tense", "aggressive", "lively", "peaceful"]
    feedback_dict = {}
    for i in xrange(2):
        for index, feedback in enumerate(feedbacks):
            key = i * 5 + index
            feedback_dict[key] = feedback

    return feedback_dict

def search_song(artist, song):
    results = []
    if artist != None and song != None:
        results = Song.objects.filter(artist__name__icontains=artist).filter(name__icontains=song)
    # search by artist
    elif artist != None:
        results = Song.objects.filter(artist__name__icontains=artist)
    # search by song
    elif song != None:
        results = Song.objects.filter(name__icontains=song)
    # none
    else:
        pass

    return results

def add_perference_song(user_id, song_id, like_type):

    if like_type == "1":
        song = Preference(user_id=user_id, song_id=song_id)
        song.save()
    else:
        Preference.objects.filter(user_id=user_id, song_id=song_id).delete()

def get_pagination_contents(paginator, page):

    try:
        contents = paginator.page(page)
    except PageNotAnInteger:
        contents = paginator.page(1)
    except EmptyPage:
        contents = paginator.page(paginator.num_pages)

    return contents

def get_song_obj(songs):
    
    results = Song.objects.filter(id__in=songs)

    return results

def get_top_k_songs(user):

    r = redis.Redis(host='localhost', port=6379, db=0)
    key = "rankings_" + str(user.id)
    songs = r.lrange(key, 0, 9)
    songs = np.array(songs, dtype=np.int64)
    return songs

def get_top_song(user):

    r = redis.Redis(host='localhost', port=6379, db=0)
    song = r.hget("top_song", str(user.id))
    return int(song)

def add_user_recommend_song(user_id, song_id):

    obj, created = RecommendSong.objects.get_or_create(user_id=user_id, song_id=song_id)

def count_recommend_songs(user_id):

    return RecommendSong.objects.filter(user_id=user_id).count()

def refrash_recommend_songs(user_id):

    RecommendSong.objects.filter(user_id=user_id).delete()

"""
next_page:
    1: interaction_page
    2: recommend_song_page
    3: questionnaire_page
"""
def create_like_song(user_id, song_id, recommend_type):

    next_page = 1 if recommend_type else 2
    like_song_by_type = LikeSong.objects.filter(user_id=user_id, recommend_type=recommend_type)
    if len(like_song_by_type) != 0:
        like_song_by_type.update(song_id=song_id)
    else:
        obj, created = LikeSong.objects.get_or_create(user_id=user_id, song_id=song_id, recommend_type=recommend_type)

    like_counts = LikeSong.objects.filter(user_id=user_id)
    if len(like_counts) == 2:
        next_page = 3

    return next_page

def get_select_songs(user_id):
    results = LikeSong.objects.filter(user_id=user_id).order_by('recommend_type')
    return results

def save_questionnaire(user_id, comparison, interaction_rate, recommend_rate, free_content):

    obj, created = Questionnaire.objects.get_or_create(user_id=user_id, comparison=comparison, interaction_rate=interaction_rate, recommend_rate=recommend_rate, free_content=free_content)

