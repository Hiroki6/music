# -*- coding:utf-8 -*-
from recommendation.helpers import emotion_helper, common_helper, relevant_helper
import sys
sys.dont_write_bytecode = True 

def emotion_search(request, emotions, situation, learning=True):
    """
    印象語フィードバック用の検索関数
    """
    song_obj = None
    user_id = request.user.id
    if learning:
        song_obj = emotion_helper.learning_and_get_song(str(user_id), emotions)
        common_helper.save_search_song(user_id, song_obj[0].id, situation, 1)
    else:
        song_obj = emotion_helper.get_top_song(str(user_id), situation, emotions, 1)
    return song_obj

def relevant_search(request, emotions, situation, learning=True):
    """
    適合性フィードバック用の検索関数
    """
    song_obj = None
    user_id = request.user.id
    if learning:
        song_obj = relevant_helper.learning_and_get_song(str(user_id), emotions)
        common_helper.save_search_song(user_id, song_obj[0].id, situation, 0)
    else:
        song_obj = relevant_helper.get_top_song(str(user_id), situation, emotions, 0)
    return song_obj

def get_relevant_back_song(user_id, song_id, situation):
    """
    戻るボタンを押した時の楽曲取得
    """
    return relevant_helper.get_back_song(user_id, song_id, situation)

def baseline_search(request, emotion, feedback=True):
    """
    印象語フィードバックのベースライン
    """
    song_obj = []

def check_search_request(request, feedback_type):
    """
    印象語検索におけるチェック
    """
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
    """
    検索手法別に検索を行う
    """
    situation, emotions = common_helper.get_now_search_situation(request.user.id)
    if feedback_type == "emotion":
        songs = emotion_search(request, emotions, situation, False)
    else:
        songs = relevant_search(request, emotions, situation, False)
    return songs, situation, emotions

def save_search_situation(request):
    """
    選択した状況と印象語を永続化する
    """
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
    """
    特定のユーザーモデルの初期化
    """
    user_id = request.user.id
    feedback_type = request.POST["search_type"]
    common_helper.init_user_model(user_id, feedback_type)

def all_refresh(request):
    """
    すべてのユーザーモデルの初期化
    """
    user_id = request.user.id
    feedback_type = request.POST["search_type"]

def get_common_params(request):
    """
    印象語と状況の取得
    """
    emotions = request.POST.getlist("emotion")
    situation = int(request.POST['situation'])
    user_id = request.user.id
    return user_id, situation, emotions

def get_feedback_params(request):
    """
    フィードバックパラメーターの取得
    """
    feedback_type = request.POST['select_feedback']
    song_id = int(request.POST['song_id'])
    user_id, situation, emotions = get_common_params(request)
    return user_id, situation, emotions, song_id, feedback_type

def get_back_params(request):
    """
    戻るボタンの時のパラメーター取得
    """
    song_id = int(request.POST['back'])
    user_id, situation, emotions = get_common_params(request)
    return user_id, situation, emotions, song_id

def get_search_songs(request, feedback_type):
    """
    検索された楽曲の一覧を取得する
    """
    situation, emotions = common_helper.get_now_search_situation(request.user.id)
    song_objs = common_helper.get_search_songs(request.user.id, situation, feedback_type)
    return situation, song_objs

def get_best_song_param(request):
    song_id = int(request.POST["best_song"])
    situation = int(request.POST["situation"])
    return song_id, situation

def get_next_url(user_id, situation):
    """
    次に誘導するページのurlを取得する
    relevant_feedback_single: 適合性フィードバックのページ
    emotion_feedback_single: 印象語フィードバックのページ
    /: 次の状況の検索
    @return: url
    """
    not_feedback_type = common_helper.get_not_feedback_type(user_id, situation)
    return "/recommendation/" + not_feedback_type
