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
from recommendation.factorization_machines import recommend_lib
from django.contrib.sites.models import Site
from recommendation.helpers import recommend_helper
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.csrf import csrf_protect
import time
import sys
sys.dont_write_bytecode = True 

initial_strings = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"]
@login_required
def index(request):
    if request.method == 'POST':
        song_id = request.POST['song_id']
        Preference.objects.filter(user_id=request.user.id, song_id=song_id).delete()
    user = request.user
    user_id = user.id
    results = Preference.objects.filter(user=user_id)
    paginator = Paginator(results, 10)
    page = request.GET.get("page")
    contents = recommend_helper.get_pagination_contents(paginator, page)
    return render(request, 'recommendation/index.html', {'user': user, 'results': contents})

"""
音楽推薦
"""
# フィードバック
@login_required
def feedback(request):
    error_msg = ""
    try:
        feedback_value = request.POST['select-feedback']
        if feedback_value == "-1":
            error_msg = "フィードバックを選択してください"
            #return redirect('/recommendation/recommend_song/')
            return recommend_song(request, error_msg)
        song_id = request.POST['song']
    except KeyError:
        pass
    start_time = time.time()
    rm_obj = recommend_lib.create_recommend_obj(request.user.id, 8)
    rm_obj.relearning(feedback_value)
    print time.time() - start_time
    return redirect('/recommendation/recommend_song/')

# 検索
@login_required
def search(request):
    results = []
    artist = ""
    song = ""
    is_result = 0
    if request.method == 'POST':
        like_type = request.POST['like_type']
        song_id = request.POST['song_id']
        recommend_helper.add_perference_song(request.user.id, song_id, like_type)
        return redirect('/recommendation/search/')
    if request.method == 'GET':
        form = MusicSearchForm(request.GET)
        if form.data.has_key('artist') and form.data.has_key('song'):
            artist = form.data['artist']
            song = form.data['song']
            results = recommend_helper.search_song(artist, song)
            is_result = 1 if len(results) == 0 else 2
    else:
        form = MusicSearchForm()
    paginator = Paginator(results, 10)
    page = request.GET.get("page")
    contents = recommend_helper.get_pagination_contents(paginator, page)
    songs = recommend_helper.get_user_preference(request.user.id)
    params = "&artist=" + artist + "&song=" + song
    return render(request, 'recommendation/search.html', {'form': form, 'artist': artist, 'song': song, 'results': contents, 'is_result': is_result, 'user': request.user, 'songs': songs, 'page': page, 'params': params})

# アーティスト一覧
@login_required
def artists(request):
    artists = Artist.objects.all()
    artist_number = len(artists)
    return render(request, 'recommendation/artists.html', {'artists': artists, 'initial_strings': initial_strings, 'artist_number': artist_number, 'user': request.user})

# アーティストごとの楽曲
@login_required
def artist(request, artist_id):
    page = 0
    if request.method == 'POST':
        like_type = request.POST['like_type']
        song_id = request.POST['song_id']
        recommend_helper.add_perference_song(request.user.id, song_id, like_type)
        return redirect('/recommendation/artist/'+artist_id)
    if request.GET.has_key("page"):
        page = int(request.GET["page"])
    index = page * 10
    songs = recommend_helper.get_user_preference(request.user.id)
    results = Song.objects.filter(artist=artist_id)
    artist_name = results[0].artist.name
    paginator = Paginator(results, 10)
    page = request.GET.get("page")
    contents = recommend_helper.get_pagination_contents(paginator, page)
    return render(request, 'recommendation/artist.html', {'results': contents, 'user': request.user, 'songs': songs, 'artist': artist_id, 'page': page, 'artist_name': artist_name})

# 指定した頭文字から始まるアーティスト名
@login_required
def artists_initial(request, init_string):
    artists = Artist.objects.filter(name__istartswith=init_string)
    artist_number = len(artists)
    return render(request, 'recommendation/artists.html', {'artists': artists, 'initial_strings': initial_strings, 'artist_number': artist_number, 'user': request.user})

# ユーザー作成
def new(request):
    form = UserCreationForm()
    error_msg = ""
    if request.method == 'POST':
        user_name = request.POST['username']
        password = request.POST['password1']
        password_confirm = request.POST['password2']
        if password != password_confirm:
            error_msg = "パスワードが一致しません"
        else:
            new_user = User.objects.create_user(user_name, None, password)
            new_user.save()
            return redirect('/login')

    c = {'form': form, 'error_msg': error_msg}
    c.update(csrf(request))
    return render(request, 'recommendation/new.html', c)

# ユーザーページ
def user(request):
    user = request.user
    user_id = user.id
    result = Preference.objects.filter(user=user_id)
    return render(request, 'recommendation/user.html', {'user': user})

"""
この部分でFMを使う
"""
@login_required
def recommend_song(request, error_msg = ""):
    user = request.user
    song = recommend_helper.get_top_song(user)
    song_obj = Song.objects.filter(id=song)
    recommend_helper.add_user_recommend_song(user.id, song)
    feedback_dict = recommend_helper.get_feedback_dict()
    finish_flag = 1 if recommend_helper.count_recommend_songs(user.id) >= 10 else 0
    return render(request, 'recommendation/recommend_song.html', {'user': user, 'songs': song_obj, 'feedback_dict': feedback_dict, 'finish_flag': finish_flag, 'error_msg': error_msg})

@login_required
def recommend_songs(request):
    user = request.user
    songs = recommend_helper.get_top_k_songs(user)
    results = Song.objects.filter(id__in=songs)
    return render(request, 'recommendation/recommend_songs.html', {'user': user, 'results': results})

@login_required
def interaction_songs(request):
    if request.method == 'POST':
        user_id = request.POST['user_id']
        recommend_helper.refrash_recommend_songs(user_id)
        return redirect('/recommendation/recommend_song/')
    user = request.user
    results = RecommendSong.objects.filter(user=user.id)
    return render(request, 'recommendation/interaction_songs.html', {'user': user, 'results': results})

@login_required
def select_song(request):
    user = request.user
    next_page = 2
    if request.method == 'POST':
        recommend_type = request.POST['recommend_type']
        if request.POST.has_key("like_by_recommend"):
            song_id = request.POST['like_by_recommend']
            next_page = recommend_helper.create_like_song(user.id, song_id, recommend_type)
            print recommend_type
    if next_page == 1:
        return redirect('/recommendation/recommend_song/')
    elif next_page == 2:
        return redirect('/recommendation/recommend_songs/')
    else:
        return redirect('/recommendation/questionnaire/')

@login_required
def questionnaire(request):
    results = recommend_helper.get_select_songs(request.user.id)
    recommend_all_songs = recommend_helper.get_recommend_all_songs(request.user)
    recommend_all_song_map = dict(zip(range(0, len(recommend_all_songs)), recommend_all_songs))
    error_msg = ""
    # すでに回答しているかどうか
    is_answer = recommend_helper.judge_answer(request.user.id)
    if request.method == 'POST':
        if request.POST.has_key('q1') and request.POST.has_key('q2') and request.POST.has_key('q3') and request.POST.has_key('q4') and request.POST.has_key('free_content'):
            comparison = request.POST['q1']
            interaction_rate = request.POST['q2']
            recommend_rate = request.POST['q3']
            compare_method = request.POST['q4']
            song_nums = 0
            for i in xrange(len(recommend_all_song_map)):
                if request.POST[str(i)] == "1":
                    song_nums += 1
            free_content = request.POST['free_content']
            helpers.save_questionnaire(request.user.id, comparison, interaction_rate, recommend_rate, song_nums, compare_method, free_content)
            return redirect('/recommendation/end/')
        else:
            error_msg = "全て選択してください"
    print error_msg
    return render(request, 'recommendation/questionnaire.html', {'results': results, 'error_msg': error_msg, 'recommend_all_song_map': recommend_all_song_map, 'is_answer': is_answer})

@login_required
def end(request):
    return render(request, 'recommendation/end.html')
