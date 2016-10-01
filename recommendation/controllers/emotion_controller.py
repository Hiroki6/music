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
適合性フィードバック(10曲)
"""
@login_required
def relevant_feedback_multi(request):
    k_songs, error_msg = _emotion_search(request, 10)
    return render(request, 'emotions/relevant_feedback.html', {'songs': k_songs, 'url': "relevant_feedback_multi", 'error_msg': error_msg, "multi_flag": True})

"""
印象語フィードバック(10曲)
"""
@login_required
def emotion_feedback_multi(request):
    k_songs, error_msg = _emotion_search(request, 10)
    return render(request, 'emotions/emotion_feedback.html', {'songs': k_songs, 'url': "emotion_feedback_multi", 'error_msg': error_msg, "multi_flag": True})

"""
適合性フィードバック(1曲)
"""
@login_required
def relevant_feedback_single(request):
    emotion = 0
    songs = []
    error_msg = ""
    if request.method == 'GET' and request.GET.has_key("emotion-search"):
        emotion = int(request.GET['emotion-search'])
        if emotion == 0:
            error_msg = "印象語を選択してください"
        songs = _relevant_search(request, emotion, False)
    if request.method == 'POST':
        # redis初期化
        if request.POST.has_key("refresh"):
            user_id = request.user.id
            emotion_helper.init_user_model(user_id, "relevant")
        # フィードバック
        else:
            song_id = request.POST["song_id"]
            relevant_type = request.POST["relevant_type"]
            emotion = int(request.POST['emotion'])
            user_id = request.user.id
            emotion_helper.save_user_relevant_song(int(user_id), int(song_id), int(relevant_type))
            songs = _relevant_search(request, emotion)
    search_emotion = emotion_map[emotion]
    return render(request, 'emotions/relevant_feedback.html', {'songs': songs, 'url': "relevant_feedback_single", 'error_msg': error_msg, "multi_flag": False, "emotion": emotion, "search_emotion": search_emotion})

"""
印象語フィードバック(1曲)
"""
@login_required
def emotion_feedback_single(request):
    emotion = 0
    songs = []
    error_msg = ""
    feedback_dict = common_helper.get_feedback_dict()
    if request.method == "POST" and request.POST.has_key('select-feedback'):
        feedback_value = request.POST['select-feedback']
        if feedback_value == "-1":
            error_msg = "フィードバックを選択してください"
        else:
            emotion = int(request.POST['emotion'])
            song_id = request.POST['song']
    if request.method == 'GET' and request.GET.has_key("emotion-search"):
        emotion = int(request.GET['emotion-search'])
        if emotion == 0:
            error_msg = "印象語を選択してください"
        songs = _relevant_search(request, emotion, False)
    search_emotion = emotion_map[emotion]
    return render(request, 'emotions/emotion_feedback.html', {'songs': songs, 'url': "emotion_feedback_single", 'error_msg': error_msg, "multi_flag": False, "emotion": emotion, "search_emotion": search_emotion, "url": "emotion_feedback_single", 'feedback_dict': feedback_dict})

def _emotion_search(request, k):
    error_msg, emotion = _check_search_request(request)
    k_songs = []
    if error_msg != "":
        songs = emotion_helper.search_by_emotion(int(emotion))
        k_songs = emotion_helper.get_random_k_songs(k, songs)
    
    return k_songs, error_msg

"""
適合性用フィードバック用の検索関数
最終的にはkを引数として渡す
"""
def _relevant_search(request, emotion, learning=True):
    song_obj = []
    if learning:
        song_obj = emotion_helper.learning_and_get_song_by_relevant(str(request.user.id), emotion)
    else:
        song_obj = emotion_helper.get_top_song_relevant(str(request.user.id), emotion)
    return song_obj

def _check_search_request(request):
    error_msg = ""
    emotion = "0"
    if request.method == 'GET' and request.GET.has_key("emotion-search"):
        emotion = request.GET['emotion-search']
        if emotion == "0":
            error_msg = "印象語を選択してください"
    return error_msg, int(emotion)

