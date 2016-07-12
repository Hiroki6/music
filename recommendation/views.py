# -*- coding:utf-8 -*-
from django.shortcuts import render, redirect

from django.template import Context, loader
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .models import Song, Artist, Preference
from forms import MusicSearchForm
from django.db.models import Q
from django.contrib.auth.forms import UserCreationForm
from django.core.context_processors import csrf
from django.contrib.auth.models import User
from fm import recommend_lib
from django.contrib.sites.models import Site
from helpers import *
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
    return render(request, 'recommendation/index.html', {'user': user, 'results': results})

# フィードバック
@login_required
def feedback(request):
    try:
        feedback_value = request.POST['select-feedback']
        song_id = request.POST['song']
    except KeyError:
        pass
    rm_obj = recommend_lib.create_recommend_obj(request.user.id, 16)
    rm_obj.relearning(feedback_value)
    return redirect('/recommendation/recommend_song/')

# 検索
@login_required
def search(request):
    results = []
    artist = ""
    song = ""
    page = 0
    if request.method == 'POST':
        like_type = request.POST['like_type']
        if like_type == "1":
            song_id = request.POST['song_id']
            song = Preference(user_id=request.user.id, song_id=song_id)
            song.save()
        else:
            song_id = request.POST['song_id']
            Preference.objects.filter(user_id=request.user.id, song_id=song_id).delete()
        return redirect('/recommendation/search/')
    if request.method == 'GET':
        form = MusicSearchForm(request.GET)
        if form.data.has_key('artist') and form.data.has_key('song'):
            artist = form.data['artist']
            song = form.data['song']
        results = search_song(artist, song)
    else:
        form = MusicSearchForm()
    if request.GET.has_key("page"):
        page = int(request.GET["page"])
    index = page * 10
    next_page = len(results) > index+10
    is_result = True if len(results) == 0 else False
    results = results[index:index+10] if len(results) >= index+10 else results[index:]
    songs = get_user_preference(request.user.id)
    return render(request, 'recommendation/search.html', {'form': form, 'artist': artist, 'song': song, 'results': results, 'is_result': is_result, 'user': request.user, 'songs': songs, 'page': page, 'next_page': next_page})

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
        if like_type == "1":
            song_id = request.POST['song_id']
            song = Preference(user_id=request.user.id, song_id=song_id)
            song.save()
        else:
            song_id = request.POST['song_id']
            Preference.objects.filter(user_id=request.user.id, song_id=song_id).delete()
        return redirect('/recommendation/artist/'+artist_id+"/")
    if request.GET.has_key("page"):
        page = int(request.GET["page"])
    index = page * 10
    songs = get_user_preference(request.user.id)
    results = Song.objects.filter(artist__id=artist_id)
    next_page = len(results) > index+10
    results = results[index:index+10] if len(results) >= index+10 else results[index:]
    return render(request, 'recommendation/artist.html', {'results': results, 'user': request.user, 'songs': songs, 'artist': artist_id, 'page': page, 'next_page': next_page})

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
def recommend_song(request):
    user = request.user
    rm_obj = recommend_lib.create_recommend_obj(user.id, 16)
    songs = recommend_lib.get_top_song(rm_obj)
    #songs = get_user_not_listening_songs(user.id)
    feedback_dict = get_feedback_dict()
    return render(request, 'recommendation/recommend_song.html', {'user': user, 'song': songs[4], 'feedback_dict': feedback_dict})

def recommend_songs(request):
    user = request.user
    rm_obj = recommend_lib.create_recommend_obj(user.id, 16)
    songs = recommend_lib.get_rankings(rm_obj)
    songs = songs[:10]
    #songs = get_user_not_listening_songs(user.id)
    return render(request, 'recommendation/recommend_songs.html', {'user': user, 'songs': songs[:50]})
