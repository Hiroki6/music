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
situation_map = {0: "", 1: "運動中", 2: "起床時", 3: "作業中", 4: "通学中", 5: "就寝時", 6: "単純に音楽を聴く時　"}
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
    emotions = []
    songs = []
    error_msg = ""
    situation = 0
    if request.method == 'POST':
        # redis初期化
        if request.POST.has_key("refresh"):
            _refresh(request, "relevant")
        # フィードバック
        else:
            user_id, song_id, situation, emotions, feedback_type = _get_feedback_params(request)
            emotion_helper.save_user_relevant_song(int(user_id), int(song_id), int(feedback_type))
            if feedback_type == "0":
                songs = _relevant_search(request, emotions, False)
            else:
                songs = _relevant_search(request, emotions)
    if request.method == 'GET' and request.GET.has_key("situation") and request.GET.has_key("emotion"):
        songs, situation, emotions, error_msg = _check_search_request(request, "relevant")
    search_situation = situation_map[situation]
    return render(request, 'emotions/relevant_feedback.html', {'songs': songs, 'url': "relevant_feedback_single", 'error_msg': error_msg, "multi_flag": False, "emotions": emotions, "search_situation": search_situation, "situation": situation})

"""
印象語フィードバック(1曲)
"""
@login_required
def emotion_feedback_model(request):
    emotions = []
    songs = []
    error_msg = ""
    situation = 0
    feedback_dict = common_helper.get_feedback_dict()
    if request.method == "POST":
        # redis初期化
        if request.POST.has_key("refresh"):
            _refresh(request, "emotion")
        else:
            user_id, song_id, situation, emotions, feedback_type = _get_feedback_params(request)
            if feedback_type == "-1":
                error_msg = "フィードバックを選択してください"
                songs = _emotion_search(request, emotions, False)
            else:
                # 永続化
                emotion_helper.save_user_emotion_song(user_id, song_id, situation, feedback_type)
                # 再推薦
                if feedback_type == "11":
                    songs = _emotion_search(request, emotions, False)
                # 学習
                else:
                    songs = _emotion_search(request, emotions)
    if request.method == 'GET' and request.GET.has_key("situation") and request.GET.has_key("emotion"):
        songs, situation, emotions, error_msg = _check_search_request(request, "emotion")
    search_situation = situation_map[situation]
    return render(request, 'emotions/emotion_feedback.html', {'songs': songs, 'url': "emotion_feedback_single", 'error_msg': error_msg, "multi_flag": False, "emotions": emotions, "search_situation": search_situation, "url": "emotion_feedback_single", 'feedback_dict': feedback_dict, "situation": situation})

@login_required
def emotion_feedback_baseline(request):
    emotion = 0
    songs = []
    error_msg = ""
    feedback_dict = common_helper.get_feedback_dict()

"""
印象語フィードバック用の検索関数
"""
def _emotion_search(request, emotions, learning=True):
    song_obj = []
    if learning:
        song_obj = emotion_helper.learning_and_get_song_by_emotion(str(request.user.id), emotions)
    else:
        song_obj = emotion_helper.get_top_song_emotion(str(request.user.id), emotions)
    return song_obj

"""
適合性フィードバック用の検索関数
"""
def _relevant_search(request, emotions, learning=True):
    song_obj = []
    if learning:
        song_obj = emotion_helper.learning_and_get_song_by_relevant(str(request.user.id), emotions)
    else:
        song_obj = emotion_helper.get_top_song_relevant(str(request.user.id), emotions)
    return song_obj

"""
印象語フィードバックのベースライン
"""
def _baseline_search(request, emotion, feedback=True):
    song_obj = []

"""
印象語検索におけるチェック
"""
def _check_search_request(request, feedback_type):
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
        if feedback_type == "emotion":
            songs = _emotion_search(request, emotions, False)
        else:
            songs = _relevant_search(request, emotions, False)
    return songs, int(situation), emotions, error_msg

def _refresh(request, feedback_type):
    user_id = request.user.id
    emotion_helper.init_user_model(user_id, feedback_type)

def _get_feedback_params(request):
    feedback_type = request.POST['select_feedback']
    emotions = request.POST.getlist("emotion")
    situation = int(request.POST['situation'])
    song_id = int(request.POST['song_id'])
    user_id = request.user.id
    return user_id, song_id, situation, emotions, feedback_type
