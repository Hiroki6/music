# -*- coding:utf-8 -*-
from recommendation.helpers import emotion_helper, common_helper, relevant_helper
import codecs
import sys
sys.dont_write_bytecode = True 

def init_search(request, emotions, situation):
    """
    初期の検索
    """
    song_objs = common_helper.get_init_search_songs(request.user.id, situation, emotions)
    return song_objs

def emotion_search(request, emotions, situation, learning=True):
    """
    印象語フィードバック用の検索関数
    """
    song_obj = None
    user_id = request.user.id
    if learning:
        song_obj = emotion_helper.learning_and_get_song(str(user_id), emotions, situation)
        common_helper.save_search_song(user_id, song_obj[0].id, situation, 1)
    else:
        song_obj = emotion_helper.get_top_song(str(user_id), situation, emotions, 1)
    return song_obj

def relevant_search(request, emotions, situation, learning=True):
    """
    適合性フィードバック用の検索関数
    """
    song_obj = None
    user_id = request.user.id
    if learning:
        song_obj = relevant_helper.learning_and_get_song(str(user_id), situation, emotions)
        common_helper.save_search_song(user_id, song_obj[0].id, situation, 0)
    else:
        song_obj = relevant_helper.get_top_song(str(user_id), situation, emotions, 0)
    return song_obj

def get_relevant_back_song(user_id, song_id, situation):
    """
    戻るボタンを押した時の楽曲取得
    """
    return relevant_helper.get_back_song(user_id, song_id, situation)

def baseline_search(request, emotion, feedback=True):
    """
    印象語フィードバックのベースライン
    """
    song_obj = []

def check_search_request(request, feedback_type):
    """
    印象語検索におけるチェック
    """
    error_msg = ""
    songs = []
    situation = 0
    situation = request.GET['situation']
    emotions = request.GET.getlist("emotion")
    if situation == "0":
        error_msg = "状況を選択してください"
    elif len(emotions) <= 0:
        error_msg = "印象語を少なくとも一つ選んでください"
    else:
        common_helper.save_situation_and_emotion(request.user.id, situation, emotions)
        if feedback_type == "emotion":
            songs = emotion_search(request, emotions, situation, False)
        else:
            songs = relevant_search(request, emotions, situation, False)
    return songs, int(situation), emotions, error_msg

def search_songs(request, feedback_type):
    """
    検索手法別に検索を行う
    """
    situation, emotions = common_helper.get_now_search_situation(request.user.id)
    if feedback_type == "emotion":
        songs = emotion_search(request, emotions, situation, False)
    else:
        songs = relevant_search(request, emotions, situation, False)
    return songs, situation, emotions

def save_search_situation(request):
    """
    選択した状況と印象語を永続化する
    """
    error_msg = ""
    songs = []
    situation = 0
    situation = request.GET['situation']
    emotions = request.GET.getlist("emotion")
    if situation == "0":
        error_msg = "状況を選択してください"
    elif len(emotions) <= 0:
        error_msg = "印象語を少なくとも一つ選んでください"
    else:
        common_helper.save_situation_and_emotion(request.user.id, situation, emotions)
    return error_msg

def refresh(request, feedback_type):
    """
    特定のユーザーモデルの初期化
    """
    user_id = request.user.id
    feedback_type = request.POST["search_type"]
    common_helper.init_user_model(user_id, feedback_type)

def all_refresh(request):
    """
    すべてのユーザーモデルの初期化
    """
    user_id = request.user.id
    feedback_type = request.POST["search_type"]

def get_common_params(request):
    """
    印象語と状況の取得
    """
    emotions = request.POST.getlist("emotion")
    situation = int(request.POST['situation'])
    user_id = request.user.id
    return user_id, situation, emotions

def get_feedback_params(request):
    """
    フィードバックパラメーターの取得
    """
    feedback_type = request.POST['select_feedback']
    song_id = int(request.POST['song_id'])
    user_id, situation, emotions = get_common_params(request)
    return user_id, situation, emotions, song_id, feedback_type

def get_back_params(request):
    """
    戻るボタンの時のパラメーター取得
    """
    song_id = int(request.POST['back'])
    user_id, situation, emotions = get_common_params(request)
    return user_id, situation, emotions, song_id

def get_search_songs(request, feedback_type):
    """
    feedback_typeを満たす検索で視聴した楽曲の一覧を取得する
    """
    situation, emotions = common_helper.get_now_search_situation(request.user.id)
    song_objs = common_helper.get_search_songs(request.user.id, situation, feedback_type)
    return situation, song_objs

def get_best_song_param(request):
    song_id = int(request.POST["best_song"])
    situation = int(request.POST["situation"])
    return song_id, situation

def get_next_url(user_id, situation):
    """
    次に誘導するページのurlを取得する(フィードバック別)
    relevant_feedback_single: 適合性フィードバックのページ
    emotion_feedback_single: 印象語フィードバックのページ
    /: 次の状況の検索
    @return: url
    """
    not_feedback_type = common_helper.get_not_feedback_type(user_id, situation)
    if not_feedback_type == 0:
        return "/recommendation/emotion_feedback_single/"
    elif not_feedback_type == 1:
        return "/recommendation/relevant_feedback_single/"
    else:
        return "/recommendation/"

def get_next_url_for_all_search(user_id, situation):
    """
    次に誘導するページのurlを取得する(両方のフィードバック)
    relevant_feedback_single: 適合性フィードバックのページ
    emotion_feedback_single: 印象語フィードバックのページ
    /: 次の状況の検索
    @return: url
    """
    not_feedback_type = common_helper.get_not_feedback_type(user_id, situation)
    if not_feedback_type == 0:
        return "/recommendation/emotion_feedback_single/"
    elif not_feedback_type == 1:
        return "/recommendation/relevant_feedback_single/"
    else:
        return "/recommendation/listening_songs/" + str(situation)

def get_like_songids_and_types(request):
    """
    選択された好きな楽曲3つを取得
    """
    song_ids = request.POST.getlist("best_song")
    feedback_types = []
    for song_id in song_ids:
        feedback_types.append(request.POST["feedback_type_" + song_id])
    return map(int, song_ids), map(int, feedback_types)


def process_questionnaire(request):
    if request.POST.has_key('q1') and request.POST.has_key('q2') and request.POST.has_key('q3'):
        relevant_rate = request.POST['q1']
        emotion_rate = request.POST['q2']
        comparison = request.POST['q3']
        free_content = request.POST['free_content']
        common_helper.save_emotion_questionnaire(request.user.id, relevant_rate, emotion_rate, comparison)
        # free_contentがあれば保存
        if len(free_content) > 0:
            _write_free_content(request.user.id, free_content)
        return True
    else:
        return False

def get_last_top_songs_by_type(user_id, feedback_type):
    """
    終了後のtop_kの楽曲オブジェクトをtypeによって取得する
    """
    song_objs = []
    if feedback_type == 0:
        song_objs = relevant_helper.get_last_top_songs(user_id)
    else:
        song_objs = emotion_helper.get_last_top_songs(user_id)
    return song_objs

def get_like_songids_and_ranks(request):
    """
    選択された楽曲とrankを取得
    """
    song_ids = request.POST.getlist("best_song")
    ranks = []
    for song_id in song_ids:
        ranks.append(request.POST["rank_" + song_id])
    return map(int, song_ids), map(int, ranks)

def _write_free_content(user_id, free_content):
    print "test"
    f = codecs.open("free_content.txt", "a")
    f.write("user: " + str(user_id) + "\n")
    free_content = free_content.encode("utf-8")
    f.write(free_content + "\n")
    f.write("\n")
    f.close()

