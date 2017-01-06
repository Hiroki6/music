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
from recommendation.helpers import emotion_helper, common_helper, relevant_helper
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.csrf import csrf_protect
import time
import sys
sys.dont_write_bytecode = True 
from package import *

emotion_map = {0: "", 1: "calm", 2: "tense", 3: "aggressive", 4: "lively", 5: "peaceful"}
situation_map = {0: "", 1: "運動中", 2: "起床時", 3: "作業中", 4: "通勤中", 5: "就寝時", 6: "運転中"}
#situation_map = {0: "", 1: "運動中", 2: "起床時", 3: "作業中", 4: "通学中", 5: "就寝時", 6: "純粋に音楽を聴く時"}

@login_required
def index(request):
    """
    印象語検索
    状況の選択
    """
    error_msg = ""
    print request.user.id
    situations = common_helper.get_situations_map(request.user.id)
    emotions = common_helper.get_search_emotions_map()
    if request.GET.has_key("situation"):
        error_msg = save_search_situation(request)
        if error_msg == "":
            return redirect("/recommendation/select_search/")
    common_helper.init_all_user_model(str(request.user.id))
    return render(request, 'emotions/select_situation.html', {"error_msg": error_msg, "search_flag": False, "situations": situations, "emotions": emotions})

@login_required
def select_search(request):
    """
    検索手法の選択
    """
    is_init = True
    situation, emotions = common_helper.get_now_search_situation(request.user.id)
    songs = []
    if request.method == 'POST':
        song_ids, ranks = get_like_songids_and_ranks(request)
        common_helper.save_init_rank_songs(request.user.id, situation, song_ids, ranks)
        is_init = False
    if is_init:
        songs = init_search(request, emotions, situation)
    return render(request, 'emotions/select_search.html', {"is_init": is_init, "songs": songs})

@login_required
def relevant_feedback(request):
    """
    適合性フィードバック(1曲)
    """
    emotions = []
    songs = []
    error_msg = ""
    situation = 0
    if request.method == 'POST':
        # 戻るボタンを押した場合（現在非公開）
        if request.POST.has_key("back"):
            user_id, situation, emotions, song_id = get_back_params(request)
            songs = relevant_helper.get_back_song(user_id, song_id, situation)
        # フィードバックを受けた場合
        else:
            user_id, situation, emotions, song_id, feedback_type = get_feedback_params(request)
            relevant_helper.save_user_song(int(user_id), int(song_id), int(feedback_type), int(situation))
            if feedback_type == "0":
                songs = relevant_search(request, emotions, situation, False)
            else:
                songs = relevant_search(request, emotions, situation)
    if request.method == 'GET':
        songs, situation, emotions = search_songs(request, "relevant")
    search_situation = situation_map[situation]
    is_back_song = common_helper.is_back_song(request.user.id, situation, songs[0].id, 0)
    listening_count = common_helper.get_count_listening(request.user.id, int(situation), "relevant")
    return render(request, 'emotions/relevant_feedback.html', {'songs': songs, 'url': "relevant_feedback_single", 'error_msg': error_msg, "emotions": emotions, "search_situation": search_situation, "situation": situation, "search_type": "relevant", "listening_count": listening_count, "is_back_song": is_back_song, "autoplay": 1, "feedback_type": 0})

@login_required
def emotion_feedback_model(request):
    """
    印象語フィードバック(1曲)
    """
    emotions = []
    songs = []
    error_msg = ""
    situation = 0
    feedback_dict = emotion_helper.get_feedback_dict()
    if request.method == "POST":
        # 戻るボタンを押した場合（現在非公開）
        if request.POST.has_key("back"):
            user_id, situation, emotions, song_id = get_back_params(request)
            songs = emotion_helper.get_back_song(user_id, song_id, situation)
        # フィードバックを受けた場合
        else:
            user_id, situation, emotions, song_id, feedback_type = get_feedback_params(request)
            if feedback_type == "-1":
                error_msg = "フィードバックを選択してください"
                songs, situation, emotions = emotion_search(request, emotions, situation, False)
            else:
                # 永続化
                emotion_helper.save_user_song(user_id, song_id, situation, feedback_type)
                # 再推薦
                if feedback_type == "7":
                    songs = emotion_search(request, emotions, situation, False)
                # 学習
                else:
                    songs = emotion_search(request, emotions, situation)
    if request.method == 'GET':
        songs, situation, emotions = search_songs(request, "emotion")
    search_situation = situation_map[situation]
    is_back_song = common_helper.is_back_song(request.user.id, situation, songs[0].id, 1)
    listening_count = common_helper.get_count_listening(request.user.id, int(situation), "emotion")
    return render(request, 'emotions/emotion_feedback.html', {'songs': songs, 'error_msg': error_msg, "emotions": emotions, "search_situation": search_situation, "url": "emotion_feedback_single", 'feedback_dict': feedback_dict, "situation": situation, "search_type": "emotion", "search_flag": True, "listening_count": listening_count, "is_back_song": is_back_song, "autoplay": 1, "feedback_type": 1})

@login_required
def emotion_feedback_baseline(request):
    emotion = 0
    songs = []
    error_msg = ""
    feedback_dict = emotion_helper.get_feedback_dict()

@login_required
def searched_songs(request, feedback_type):
    """
    検索された楽曲の一覧を表示する
    """
    error_msg = ""
    if request.method == "POST":
        if request.POST.has_key("best_song"):
            song_id, situation = get_best_song_param(request)
            # 最後に視聴した楽曲を永続化
            common_helper.save_last_song(request.user.id, situation, feedback_type)
            # ベストな楽曲を永続化
            common_helper.save_best_song(request.user.id, song_id, situation, feedback_type)
            url = get_next_url(request.user.id, situation)
            return redirect(url)
        else:
            error_msg = "楽曲を選択してください"
    situation, songs = get_search_songs(request, feedback_type)
    return render(request, 'emotions/searched_songs.html', {"songs": songs, "situation": situation, "feedback_type": feedback_type, "autoplay": 0, "error_msg": error_msg})

@login_required
def finish_search(request, situation, feedback_type):
    """
    検索終了ボタンが押された時の挙動
    まず、10曲を表示して、好きな楽曲を複数選択させる
    両方の検索が終了していれば、視聴した楽曲全て取得
    片方の検索が終了していれば、もう一方の検索条件に強制的に飛ばす
    """
    error_msg = ""
    common_helper.save_last_song(request.user.id, situation, feedback_type)
    songs = get_last_top_songs_by_type(request.user.id, int(feedback_type))
    if request.method == "POST":
        song_ids, ranks = get_like_songids_and_ranks(request)
        common_helper.save_rank_songs(request.user.id, situation, song_ids, ranks, feedback_type)
        url = get_next_url_for_all_search(request.user.id, situation)
        return redirect(url)
    return render(request, 'emotions/top_k_songs.html', {"songs": songs, "situation": situation, "feedback_type": feedback_type, "autoplay": 0})

@login_required
def listening_songs(request, situation):
    """
    その状況で視聴した全ての楽曲を表示
    """
    error_msg = ""
    if request.POST.has_key("best_song"):
        song_ids, feedback_types = get_like_songids_and_types(request)
        if len(song_ids) != 3:
            error_msg = "楽曲を３つ選択してください"
        else:
            common_helper.save_best_songs(request.user.id, situation, song_ids, feedback_types)
            url = common_helper.get_url_about_search(request.user.id)
            return redirect(url)
    songs = common_helper.get_listening_songs_by_situation(request.user.id, situation)
    return render(request, 'emotions/listening_songs.html', {"situation": situation, "songs": songs, "error_msg": error_msg})

@login_required
def questionnaire(request):
    error_msg = ""
    if request.method == "POST":
        if process_questionnaire(request):
            return redirect('/emotion_end/')
        else:
            error_msg = "全て選択してください"
    return render(request, 'emotions/questionnaire.html', {"error_msg": error_msg})

@login_required
def end(request):
    return render(request, 'emotions/end.html')

