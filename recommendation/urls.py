from django.conf.urls import url

from controllers import recommendation_controller
from controllers import emotion_controller

app_name = 'recommendation'
urlpatterns = [
    url(r'^new/$', recommendation_controller.new, name = 'new'),
    url(r'^$', recommendation_controller.index, name = 'index'),
    url(r'^feedback/$', recommendation_controller.feedback, name = 'feedback'),
    url(r'^search/$', recommendation_controller.search, name = 'search'),
    url(r'^artists/$', recommendation_controller.artists, name = 'artists'),
    url(r'^artists/(?P<init_string>\w+)$', recommendation_controller.artists_initial, name = 'artists_initial'),
    url(r'^artist/(?P<artist_id>\d+)$', recommendation_controller.artist, name = 'artist'),
    url(r'^user/$', recommendation_controller.user, name = 'user'),
    url(r'^recommend_song/$', recommendation_controller.recommend_song, name = 'recommend_song'),
    url(r'^recommend_songs/$', recommendation_controller.recommend_songs, name = 'recommend_songs'),
    url(r'^interaction_songs/$', recommendation_controller.interaction_songs, name = 'interaction_songs'),
    url(r'^select_song/$', recommendation_controller.select_song, name = 'select_song'),
    url(r'^questionnaire/$', recommendation_controller.questionnaire, name = 'questionnaire'),
    url(r'^end/$', recommendation_controller.end, name = 'end'),
    url(r'^emotion_search/$', emotion_controller.index, name = 'emotion_search'),
    url(r'^relevant_feedback_multi/$', emotion_controller.relevant_feedback_multi, name = 'relevant_feedback_multi'),
    url(r'^relevant_feedback_single/$', emotion_controller.relevant_feedback_single, name = 'relevant_feedback_single'),
    url(r'^emotion_feedback_multi/$', emotion_controller.emotion_feedback_multi, name = 'emotion_feedback_multi'),
    url(r'^emotion_feedback_single/$', emotion_controller.emotion_feedback_single, name = 'emotion_feedback_single')
    ]
