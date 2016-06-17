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

initial_strings = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"]
# Create your views here.
# @login_required
# def index(request):
#     songs = Song.objects.all()[:5]
#     feedbacks = ["calm", "tense", "aggressive", "lively", "peaceful"]
#     template = loader.get_template('recommendation/index.html')
#     context = Context({'songs': songs}, {'feedbacks': feedbacks})
#     return render(request, 'recommendation/index.html', {'songs': songs, 'feedbacks': feedbacks, 'feedback_loop': range(2), 'user': request.user})
    #return HttpResponse(template.render(context))
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
    feedback_value = request.get['example']
    songs = Song.objects.all()[3:8]
    feedbacks = ["calm", "tense", "aggressive", "lively", "peaceful"]
    template = loader.get_template('recommendation/login.html')
    return render(request, 'recommendation/index.html', {'songs': songs, 'feedbacks': feedbacks, 'feedback_loop': range(2), 'user': request.user})
    #return HttpResponse(template.render(request))

# 検索
@login_required
def search(request):
    results = []
    artist = ""
    song = ""
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
        # search by artist and song
        if len(artist) > 0 and len(song) > 0:
            results = Song.objects.filter(artist__name__icontains=artist).filter(name__icontains=song)
            pass
        # search by artist
        elif len(artist) > 0:
            results = Song.objects.filter(artist__name__icontains=artist)
            pass
        # search by song
        elif len(song) > 0:
            results = Song.objects.filter(name__icontains=song)
            pass
        # none
        else:
            pass
    else:
        form = MusicSearchForm()
    is_result = True if len(results) == 0 else False
    songs = get_user_preference(request.user.id)
    return render(request, 'recommendation/search.html', {'form': form, 'artist': artist, 'song': song, 'results': results, 'is_result': is_result, 'user': request.user, 'songs': songs})

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
    # elif request.method == 'GET':
    #     page = request.GET['page']
    page *= 10
    songs = get_user_preference(request.user.id)
    results = Song.objects.filter(artist__id=artist_id)
    if len(results) >= page+10:
        results = results[page:page+10]
    else:
        results = results[page:]
    return render(request, 'recommendation/artist.html', {'results': results, 'user': request.user, 'songs': songs})

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
    songs = get_user_not_listening_songs(user.id)
    feedback_dict = get_feedback_dict()
    return render(request, 'recommendation/recommend_song.html', {'user': user, 'songs': songs[:10], 'feedback_dict': feedback_dict})

# そのユーザーの好みの楽曲リスト取得
def get_user_preference(user_id):

    songs = []
    preferences = Preference.objects.filter(user_id=user_id)
    for preference in preferences:
        songs.append(preference.song_id)

    return songs

# ユーザーがまだ聞いていない楽曲のリスト取得
def get_user_not_listening_songs(user_id):

    listening_songs = get_user_preference(user_id)
    songs = Song.objects.exclude(id__in=listening_songs)
    return songs

def get_feedback_dict():

    feedbacks = ["calm", "tense", "aggressive", "lively", "peaceful"]
    feedback_dict = {}
    for i in xrange(2):
        for index, feedback in enumerate(feedbacks):
            key = i * 5 + index
            feedback_dict[key] = feedback

    return feedback_dict
