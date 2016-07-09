# -*- coding:utf-8 -*-
from .models import Song, Artist, Preference

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
    if len(artist) > 0 and len(song) > 0:
        results = Song.objects.filter(artist__name__icontains=artist).filter(name__icontains=song)
    # search by artist
    elif len(artist) > 0:
        results = Song.objects.filter(artist__name__icontains=artist)
    # search by song
    elif len(song) > 0:
        results = Song.objects.filter(name__icontains=song)
    # none
    else:
        pass

    return results
