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
    situations = common_helper.get_situations_map(request.user.id)
    if request.GET.has_key("situation"):
        error_msg = save_search_situation(request)
        if error_msg == "":
            return redirect("/recommendation/select_search/")
    common_helper.init_all_user_model(str(request.user.id))
    return render(request, 'emotions/select_situation.html', {"error_msg": error_msg, "search_flag": False, "situations": situations})

@login_required
def select_search(request):
    """
    検索手法の選択
    """
    is_init = True
    situation = common_helper.get_now_situation(request.user.id)
    songs = []
    if request.method == 'POST':
        song_ids, ranks = get_like_songids_and_ranks(request)
        common_helper.save_init_rank_songs(request.user.id, situation, song_ids, ranks)
        search_url = get_search_type_by_random()
        return redirect(search_url)
        is_init = False
    if is_init:
        songs = init_search(request, situation)
        common_helper.save_search_song_both_type(request.user.id, songs[0][1].id, situation)
    search_situation = situation_map[situation]
    return render(request, 'emotions/select_search.html', {"is_init": is_init, "songs": songs, "search_situation": search_situation})

@login_required
def relevant_feedback(request):
    """
    適合性フィードバック(1曲)
    """
    songs = []
    error_msg = ""
    situation = 0
    if request.method == 'POST':
        user_id, situation, song_id, feedback_type = get_feedback_params(request)
        relevant_helper.save_user_song(int(user_id), int(song_id), int(feedback_type), int(situation))
        listening_count = common_helper.get_count_listening(user_id, int(situation), "relevant")
        if feedback_type == "0":
            init_flag = common_helper.get_init_flag(user_id, situation, "relevant")
            if init_flag:
                songs = common_helper.get_next_song(user_id, situation, listening_count, 0)
            else:
                songs = relevant_search(request, situation, False)
        else:
            songs = relevant_search(request, situation)
    if request.method == 'GET':
        songs, situation = get_now_search_songs(request, "relevant")
        listening_count = common_helper.get_count_listening(request.user.id, int(situation), "relevant")
    search_situation = situation_map[situation]
    #is_back_song = common_helper.is_back_song(request.user.id, situation, songs[0].id, 0)
    return render(request, 'emotions/relevant_feedback.html', {'songs': songs, 'url': "relevant_feedback_single", 'error_msg': error_msg, "search_situation": search_situation, "situation": situation, "search_type": "relevant", "listening_count": listening_count, "autoplay": 1, "feedback_type": 0})

@login_required
def emotion_feedback_model(request):
    """
    印象語フィードバック(1曲)
    """
    songs = []
    error_msg = ""
    situation = 0
    feedback_dict = emotion_helper.get_feedback_dict()
    if request.method == "POST":
        user_id, situation, song_id, feedback_type = get_feedback_params(request)
        # 再推薦
        emotion_helper.save_user_song(user_id, song_id, situation, feedback_type)
        listening_count = common_helper.get_count_listening(user_id, int(situation), "emotion")
        if feedback_type == "7":
            init_flag = common_helper.get_init_flag(user_id, situation, "emotion")
            if init_flag:
                songs = common_helper.get_next_song(user_id, situation, listening_count, 1)
            else:
                songs = emotion_search(request, situation, False)
        # 学習
        else:
            # EmotionEmotionBasedSongにデータを永続化
            songs = emotion_search(request, situation)
    if request.method == 'GET':
        songs, situation = get_now_search_songs(request, "emotion")
        listening_count = common_helper.get_count_listening(request.user.id, int(situation), "emotion")
    search_situation = situation_map[situation]
    #is_back_song = common_helper.is_back_song(request.user.id, situation, songs[0].id, 1)
    return render(request, 'emotions/emotion_feedback.html', {'songs': songs, 'error_msg': error_msg, "search_situation": search_situation, "url": "emotion_feedback_single", 'feedback_dict': feedback_dict, "situation": situation, "search_type": "emotion", "search_flag": True, "listening_count": listening_count, "autoplay": 1, "feedback_type": 1})

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
    search_situation = situation_map[int(situation)]
    return render(request, 'emotions/top_k_songs.html', {"songs": songs, "situation": situation, "feedback_type": feedback_type, "autoplay": 0, "search_situation": search_situation})

@login_required
def listening_songs(request, situation):
    """
    その状況で視聴した全ての楽曲を表示
    """
    error_msg = ""
    if request.POST.has_key("best_song"):
        song_ids, feedback_types = get_like_songids_and_types(request)
        if len(song_ids) < 3:
            error_msg = "楽曲を３つ以上選択してください"
        else:
            common_helper.save_best_songs(request.user.id, situation, song_ids, feedback_types)
            url = common_helper.get_url_about_search(request.user.id)
            return redirect(url)
    songs = common_helper.get_listening_songs_by_situation(request.user.id, situation)
    search_situation = situation_map[int(situation)]
    return render(request, 'emotions/listening_songs.html', {"situation": situation, "songs": songs, "error_msg": error_msg, "search_situation": search_situation})

@login_required
def questionnaire(request):
    """
    最後のアンケート
    """
    error_msg = ""
    if request.method == "POST":
        if process_questionnaire(request):
            return redirect('/emotion_end/')
        else:
            error_msg = "全て選択してください"
    return render(request, 'emotions/questionnaire.html', {"error_msg": error_msg})

@login_required
def end(request):
    """
    終了時
    """
    return render(request, 'emotions/end.html')

@login_required
def one_song(request, song_id):
    """
    song_idを持つ楽曲を表示する
    主にその楽曲が再生されるかどうかなどのチェックに行う
    """
    songs = common_helper.get_song_obj(song_id)
    return render(request, 'emotions/one_song.html', {"songs": songs})
