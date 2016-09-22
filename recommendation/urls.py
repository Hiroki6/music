from django.conf.urls import url

from . import views

app_name = 'recommendation'
urlpatterns = [
    url(r'^new/$', views.new, name = 'new'),
    url(r'^$', views.index, name = 'index'),
    url(r'^feedback/$', views.feedback, name = 'feedback'),
    url(r'^search/$', views.search, name = 'search'),
    url(r'^artists/$', views.artists, name = 'artists'),
    url(r'^artists/(?P<init_string>\w+)$', views.artists_initial, name = 'artists_initial'),
    url(r'^artist/(?P<artist_id>\d+)$', views.artist, name = 'artist'),
    url(r'^user/$', views.user, name = 'user'),
    url(r'^recommend_song/$', views.recommend_song, name = 'recommend_song'),
    url(r'^recommend_songs/$', views.recommend_songs, name = 'recommend_songs'),
    url(r'^interaction_songs/$', views.interaction_songs, name = 'interaction_songs'),
    url(r'^select_song/$', views.select_song, name = 'select_song'),
    url(r'^questionnaire/$', views.questionnaire, name = 'questionnaire'),
    url(r'^end/$', views.end, name = 'end'),
    url(r'^emotion_search/$', views.emotion_search, name = 'emotion_search'),
    url(r'^relevant_feedback/$', views.relevant_feedback, name = 'relevant_feedback'),
    url(r'^emotion_feedback/$', views.emotion_feedback, name = 'emotion_feedback')
    ]
