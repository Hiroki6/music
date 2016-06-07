from django.conf.urls import url

from . import views

app_name = 'recommendation'
urlpatterns = [
    url(r'^new/$', views.new, name = 'new'),
    url(r'^$', views.index, name = 'index'),
    url(r'^$', views.feedback, name = 'feedback'),
    url(r'^search/$', views.search, name = 'search'),
    url(r'^artists/$', views.artists, name = 'artists'),
    url(r'^artists/(?P<init_string>\w+)$', views.artists_initial, name = 'artists_initial'),
    url(r'^artist/(?P<artist_id>\d+)/$', views.artist, name = 'artist'),
    url(r'^user/$', views.user, name = 'user'),
    ]
