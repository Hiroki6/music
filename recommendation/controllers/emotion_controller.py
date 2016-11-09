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
from package import *

emotion_map = {0: "", 1: "calm", 2: "tense", 3: "aggressive", 4: "lively", 5: "peaceful"}
situation_map = {0: "", 1: "運動中", 2: "起床時", 3: "作業中", 4: "通学中", 5: "就寝時", 6: "単純に音楽を聴く時　"}
"""
印象語検索
状況の選択
"""
@login_required
def index(request):
    error_msg = ""
    if request.GET.has_key("situation"):
        error_msg = save_search_situation(request)
        if error_msg == "":
            return redirect("/recommendation/select_search/")
    emotion_helper.init_all_user_model(str(request.user.id))
    return render(request, 'emotions/select_situation.html', {"error_msg": error_msg, "search_flag": False})

"""
検索手法の選択
"""
@login_required
def select_search(request):
    return render(request, 'emotions/select_search.html')

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
        user_id, song_id, situation, emotions, feedback_type = get_feedback_params(request)
        emotion_helper.save_user_relevant_song(int(user_id), int(song_id), int(feedback_type))
        if feedback_type == "0":
            songs = relevant_search(request, emotions, False)
        else:
            songs = relevant_search(request, emotions)
    if request.method == 'GET':
        songs, situation, emotions = search_songs(request, "relevant")
    search_situation = situation_map[situation]
    return render(request, 'emotions/relevant_feedback.html', {'songs': songs, 'url': "relevant_feedback_single", 'error_msg': error_msg, "multi_flag": False, "emotions": emotions, "search_situation": search_situation, "situation": situation, "search_type": "relevant"})

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
        user_id, song_id, situation, emotions, feedback_type = get_feedback_params(request)
        if feedback_type == "-1":
            error_msg = "フィードバックを選択してください"
            songs, situation, emotions = emotion_search(request, emotions, False)
        else:
            # 永続化
            emotion_helper.save_user_emotion_song(user_id, song_id, situation, feedback_type)
            # 再推薦
            if feedback_type == "11":
                songs = emotion_search(request, emotions, False)
            # 学習
            else:
                songs = emotion_search(request, emotions)
    if request.method == 'GET':
        songs, situation, emotions = search_songs(request, "emotion")
    search_situation = situation_map[situation]
    return render(request, 'emotions/emotion_feedback.html', {'songs': songs, 'error_msg': error_msg, "multi_flag": False, "emotions": emotions, "search_situation": search_situation, "url": "emotion_feedback_single", 'feedback_dict': feedback_dict, "situation": situation, "search_type": "emotion", "search_flag": True})

@login_required
def emotion_feedback_baseline(request):
    emotion = 0
    songs = []
    error_msg = ""
    feedback_dict = common_helper.get_feedback_dict()
