# -*- coding:utf-8 -*-
from django.shortcuts import render, redirect
from django.template import Context, loader
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from recommendation.models import Song, Artist, Preference
from recommendation.forms import MusicSearchForm, EmotionSearchForm
from django.db.models import Q
from django.contrib.auth.forms import UserCreationForm
from django.core.context_processors import csrf
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from recommendation.helpers import emotion_helper, common_helper
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.csrf import csrf_protect
import time
import sys
sys.dont_write_bytecode = True 

emotion_map = {0: "", 1: "calm", 2: "tense", 3: "aggressive", 4: "lively", 5: "peaceful"}
"""
印象語検索
"""
@login_required
def index(request):
    return render(request, 'emotions/emotion_search.html')

"""
適合性フィードバック(1曲)
"""
@login_required
def relevant_feedback(request):
    emotion = 0
    songs = []
    error_msg = ""
    if request.method == 'POST':
        # redis初期化
        if request.POST.has_key("refresh"):
            _refresh(request, "relevant")
        # フィードバック
        else:
            user_id, song_id, emotion, feedback_type = _get_feedback_params(request)
            emotion_helper.save_user_relevant_song(int(user_id), int(song_id), int(feedback_type))
            if feedback_type == "0":
                songs = _relevant_search(request, emotion, False)
            else:
                songs = _relevant_search(request, emotion)
    if request.method == 'GET' and request.GET.has_key("emotion_search"):
        songs, emotion, error_msg = _check_search_request(request, "relevant")
    search_emotion = emotion_map[emotion]
    return render(request, 'emotions/relevant_feedback.html', {'songs': songs, 'url': "relevant_feedback_single", 'error_msg': error_msg, "multi_flag": False, "emotion": emotion, "search_emotion": search_emotion})

"""
印象語フィードバック(1曲)
"""
@login_required
def emotion_feedback_model(request):
    emotion = 0
    songs = []
    error_msg = ""
    feedback_dict = common_helper.get_feedback_dict()
    if request.method == "POST":
        # redis初期化
        if request.POST.has_key("refresh"):
            _refresh(request, "emotion")
        else:
            user_id, song_id, emotion, feedback_type = _get_feedback_params(request)
            if feedback_type == "-1":
                error_msg = "フィードバックを選択してください"
                songs = _emotion_search(request, emotion, False)
            else:
                # 永続化
                emotion_helper.save_user_emotion_song(user_id, song_id, emotion, feedback_type)
                # 再推薦
                if feedback_type == "11":
                    songs = _emotion_search(request, emotion, False)
                # 学習
                else:
                    songs = _emotion_search(request, emotion)
    if request.method == 'GET' and request.GET.has_key("emotion_search"):
        songs, emotion, error_msg = _check_search_request(request, "emotion")
    search_emotion = emotion_map[emotion]
    return render(request, 'emotions/emotion_feedback.html', {'songs': songs, 'url': "emotion_feedback_single", 'error_msg': error_msg, "multi_flag": False, "emotion": emotion, "search_emotion": search_emotion, "url": "emotion_feedback_single", 'feedback_dict': feedback_dict})

@login_required
def emotion_feedback_baseline(request):
    emotion = 0
    songs = []
    error_msg = ""
    feedback_dict = common_helper.get_feedback_dict()

"""
印象語フィードバック用の検索関数
"""
def _emotion_search(request, emotion, learning=True):
    song_obj = []
    if learning:
        song_obj = emotion_helper.learning_and_get_song_by_emotion(str(request.user.id), emotion)
    else:
        song_obj = emotion_helper.get_top_song_emotion(str(request.user.id), emotion)
    return song_obj

"""
適合性フィードバック用の検索関数
"""
def _relevant_search(request, emotion, learning=True):
    song_obj = []
    if learning:
        song_obj = emotion_helper.learning_and_get_song_by_relevant(str(request.user.id), emotion)
    else:
        song_obj = emotion_helper.get_top_song_relevant(str(request.user.id), emotion)
    return song_obj

"""
印象語フィードバックのベースライン
"""
def _baseline_search(request, emotion, feedback=True):
    song_obj = []

def _check_search_request(request, feedback_type):
    error_msg = ""
    songs = []
    emotion = 0
    emotion = request.GET['emotion_search']
    if emotion == "0":
        error_msg = "印象語を選択してください"
    else:
        if feedback_type == "emotion":
            songs = _emotion_search(request, emotion, False)
        else:
            songs = _relevant_search(request, emotion, False)
    return songs, int(emotion), error_msg

def _refresh(request, feedback_type):
    user_id = request.user.id
    emotion_helper.init_user_model(user_id, feedback_type)

def _get_feedback_params(request):
    feedback_type = request.POST['select_feedback']
    emotion = int(request.POST['emotion'])
    song_id = int(request.POST['song_id'])
    user_id = request.user.id
    return user_id, song_id, emotion, feedback_type
