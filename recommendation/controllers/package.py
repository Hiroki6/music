# -*- coding:utf-8 -*-
from recommendation.models import Song, Artist, Preference
from recommendation.helpers import emotion_helper, common_helper
import sys
sys.dont_write_bytecode = True 

"""
印象語フィードバック用の検索関数
"""
def emotion_search(request, emotions, learning=True):
    if learning:
        return emotion_helper.learning_and_get_song_by_emotion(str(request.user.id), emotions)
    else:
        return emotion_helper.get_top_song_emotion(str(request.user.id), emotions)

"""
適合性フィードバック用の検索関数
"""
def relevant_search(request, emotions, learning=True):
    if learning:
        return emotion_helper.learning_and_get_song_by_relevant(str(request.user.id), emotions)
    else:
        return emotion_helper.get_top_song_relevant(str(request.user.id), emotions)

"""
印象語フィードバックのベースライン
"""
def baseline_search(request, emotion, feedback=True):
    song_obj = []

"""
印象語検索におけるチェック
"""
def check_search_request(request, feedback_type):
    error_msg = ""
    songs = []
    situation = 0
    situation = request.GET['situation']
    emotions = request.GET.getlist("emotion")
    if situation == "0":
        error_msg = "状況を選択してください"
    elif len(emotions) <= 0:
        error_msg = "印象語を少なくとも一つ選んでください"
    else:
        emotion_helper.save_situation_and_emotion(request.user.id, situation, emotions)
        if feedback_type == "emotion":
            songs = emotion_search(request, emotions, False)
        else:
            songs = relevant_search(request, emotions, False)
    return songs, int(situation), emotions, error_msg

def search_songs(request, feedback_type):
    situation, emotions = emotion_helper.get_now_search_situation(request.user.id)
    if feedback_type == "emotion":
        songs = emotion_search(request, emotions, False)
    else:
        songs = relevant_search(request, emotions, False)
    return songs, situation, emotions

def save_search_situation(request):
    error_msg = ""
    songs = []
    situation = 0
    situation = request.GET['situation']
    emotions = request.GET.getlist("emotion")
    if situation == "0":
        error_msg = "状況を選択してください"
    elif len(emotions) <= 0:
        error_msg = "印象語を少なくとも一つ選んでください"
    else:
        emotion_helper.save_situation_and_emotion(request.user.id, situation, emotions)
    return error_msg

def refresh(request, feedback_type):
    user_id = request.user.id
    feedback_type = request.POST["search_type"]
    emotion_helper.init_user_model(user_id, feedback_type)

def all_refresh(request):
    user_id = request.user.id
    feedback_type = request.POST["search_type"]

def get_feedback_params(request):
    feedback_type = request.POST['select_feedback']
    emotions = request.POST.getlist("emotion")
    situation = int(request.POST['situation'])
    song_id = int(request.POST['song_id'])
    user_id = request.user.id
    return user_id, song_id, situation, emotions, feedback_type
