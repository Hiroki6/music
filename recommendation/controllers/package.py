# -*- coding:utf-8 -*-
from recommendation.helpers import emotion_helper, common_helper, relevant_helper
import sys
sys.dont_write_bytecode = True 

"""
印象語フィードバック用の検索関数
"""
def emotion_search(request, emotions, situation, learning=True):
    song_obj = None
    user_id = request.user.id
    if learning:
        song_obj = emotion_helper.learning_and_get_song(str(user_id), emotions)
        common_helper.save_search_song(user_id, song_obj[0].id, situation, 1)
    else:
        song_obj = common_helper.get_top_song(str(user_id), situation, emotions, 1)
    return song_obj

"""
適合性フィードバック用の検索関数
"""
def relevant_search(request, emotions, situation, learning=True):
    song_obj = None
    user_id = request.user.id
    if learning:
        song_obj = relevant_helper.learning_and_get_song(str(user_id), emotions)
        common_helper.save_search_song(user_id, song_obj[0].id, situation, 0)
    else:
        song_obj = common_helper.get_top_song(str(user_id), situation, emotions, 0)
    return song_obj

def get_relevant_back_song(user_id, song_id, situation):
    return relevant_helper.get_back_song(user_id, song_id, situation)

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
        common_helper.save_situation_and_emotion(request.user.id, situation, emotions)
        if feedback_type == "emotion":
            songs = emotion_search(request, emotions, situation, False)
        else:
            songs = relevant_search(request, emotions, situation, False)
    return songs, int(situation), emotions, error_msg

def search_songs(request, feedback_type):
    situation, emotions = common_helper.get_now_search_situation(request.user.id)
    if feedback_type == "emotion":
        songs = emotion_search(request, emotions, situation, False)
    else:
        songs = relevant_search(request, emotions, situation, False)
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
        common_helper.save_situation_and_emotion(request.user.id, situation, emotions)
    return error_msg

def refresh(request, feedback_type):
    user_id = request.user.id
    feedback_type = request.POST["search_type"]
    common_helper.init_user_model(user_id, feedback_type)

def all_refresh(request):
    user_id = request.user.id
    feedback_type = request.POST["search_type"]

def get_common_params(request):
    emotions = request.POST.getlist("emotion")
    situation = int(request.POST['situation'])
    user_id = request.user.id
    return user_id, situation, emotions

def get_feedback_params(request):
    feedback_type = request.POST['select_feedback']
    song_id = int(request.POST['song_id'])
    user_id, situation, emotions = get_common_params(request)
    return user_id, situation, emotions, song_id, feedback_type

def get_back_params(request):
    song_id = int(request.POST['back'])
    user_id, situation, emotions = get_common_params(request)
    return user_id, situation, emotions, song_id
