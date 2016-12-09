# -*- coding:utf-8 -*-

"""
印象語検索における印象語フィードバックによるモデルの学習
"""

import numpy as np
import redis
import common_functions as common
from EmotionFeedback import cy_emotion_feedback as cy_ef
import sys
from recommendation import models
import math

HOST = 'localhost'
PORT = 6379
DB = 3

emotion_map = {0: "pop", 1: "ballad", 2: "rock"}

# 境界条件のmap
bound_map = {0: 0.000233, 1: 0.000953, 2: 0.000361}

class EmotionBaseline(object):
    """
    印象語フィードバックのベースライン
    フィードバックを受けた楽曲よりも印象値が高い楽曲を推薦する
    モデルは持たずにランダムに楽曲を検索し、そこからフィードバックを受けて新しい楽曲を推薦していく
    user: ログインユーザーID
    emotions: 検索語に選択した印象語配列
    """
    def __init__(self, user, emotions):
        self.user = user
        self.emotions = emotions

    def _save_top_song(self):
        """
        top_songの保存
        """
        common.delete_redis_key(self.r, "top_matrix_" + self.user)
        common.save_scalar(self.r, "top_song", self.user, self.top_song)
        common.save_one_dim_array(self.r, "top_matrix_"+self.user, self.top_matrix)

    def get_top_song(self):

        self.top_song = self.bound_songs[0]
        self.top_matrix = self.bound_song_tag_map[self.top_song]
        self._save_top_song()
        return self.top_song

    def set_params(self):
        self.k = 1
        self._create_k_bound_songs()

    def _create_k_bound_songs(self):
        """
        フィードバックの印象ベクトルの上位k個の学習データ作成
        """
        self._get_last_song()
        self._get_last_feedback()
        self._transform_feedback()
        self._get_bound_songs()

    def _get_last_song(self):
        """
        最後にフィードバックを受けた楽曲のidと印象ベクトル取得
        """
        self.top_song = common.get_scalar(self.r, "top_song", self.user)
        self.top_matrix = common.get_one_dim_params(self.r, "top_matrix_"+self.user)

    def _get_last_feedback(self):
        """
        最後のフィードバック情報取得
        """
        emotion_datas = models.EmotionEmotionbasedSong.objects.order_by("id").filter(user_id=int(self.user)).values()
        emotion_datas = emotion_datas.reverse()
        self.feedback = emotion_datas[0]["feedback_type"]

    def _transform_feedback(self):
        """
        feedback(1~6)を印象のベクトルに変換
        """
        if(self.feedback <= 2):
            self.plus_or_minus = 1
        else:
            self.plus_or_minus = -1
            self.feedback -= 3

    def _get_bound_songs(self):
        """
        フィードバックを受けた楽曲よりもemotionの値が高い楽曲s曲に対してranking学習を行う
        とりあえずその楽曲よりも直近で大きいs曲取得
        """
        top_song_objs = models.SearchMusicCluster.objects.filter(song_id=int(self.top_song)).values()
        emotion_value = top_song_objs[0][emotion_map[self.feedback]]
        self.bound_songs, self.bound_song_tag_map = common.get_bound_song_tag_map(emotion_value, self.k, self.plus_or_minus)

class EmotionFeedback(EmotionBaseline):
    """
    印象語フィードバックによるオンライン学習クラス
    """
    def __init__(self, user, emotions):
        EmotionBaseline.__init__(self, user, emotions)
        self._get_params_by_redis()
        self.cy_obj = cy_ef.CyEmotionFeedback(self.W)

    def _get_params_by_redis(self):
        self.r = common.get_redis_obj(HOST, PORT, DB)
        key =  "W_" + self.user
        self.W = common.get_one_dim_params(self.r, key)
 
    def set_params(self):
        """
        学習用データ作成
        """
        self._create_feedback_matrix()
    
    def set_params_k_rankings(self, k = 10):
        """
        フィードバックの印象ベクトルの上位k個の楽曲を学習するバージョン
        """
        self.k = k
        self._create_k_bound_songs()
    
    def fit(self):
        """
        学習
        """
        print "学習開始"
        X = self.feedback_matrix - self.top_matrix
        self.cy_obj.fit(X)
        self._update_params_into_redis()
 
    def k_fit(self):
        """
        上位k個のランキング学習
        上位K個の決定手法として、範囲アルファ*減衰定数の範囲で取得する
        """
        for song, tags in self.bound_song_tag_map.items():
            #if self.plus_or_minus == 1:
            X = tags - self.top_matrix
            #else:
            #    X = self.top_matrix - tags
            self.cy_obj.fit(X, True)
        self._update_params_into_redis()

    def get_top_k_songs(self, k=1):
        """
        検索対象の印象語に含まれている楽曲から回帰値の高いk個の楽曲を取得する
        """
        #songs, song_tag_map = common.get_not_listening_songs(self.user, self.emotions, "emotion")
        songs, song_tag_map = common.get_not_listening_songs_by_multi_emotion(self.user, self.emotions, "emotion")
        rankings = [(self.cy_obj.predict(tags), song_id) for song_id, tags in song_tag_map.items()]
        common.listtuple_sort_reverse(rankings)
        self.top_song = rankings[0][1]
        self.top_matrix = song_tag_map[self.top_song]
        self._save_top_song()
        song_tags = []
        if hasattr(self, "feedback"):
            common.write_top_k_songs(self.user, "emotion_k_song.txt", rankings[:10], emotion_map[self.feedback])
        else:
            common.write_top_k_songs(self.user, "emotion_k_song.txt", rankings[:10])

        return rankings[:k]

    def _create_feedback_matrix(self):
        """
        特定のユーザーによるフィードバックを反映させた楽曲の特徴ベクトル生成
        top_matrix: 推薦された楽曲配列
        feedback_matrix: フィードバックを受けたタグの部分だけ値を大きくしたもの
        """
        self._get_last_song()
        self._get_last_feedback()
        self._get_tags_by_feedback()
        self.feedback_matrix = self.top_matrix.copy()
        alpha = 0.1 if self.plus_or_minus == 1 else -0.1 # フィードバックによって+-を分ける
        for tag in enumerate(self.tags):
            self.feedback_matrix[tag[0]] += alpha/self.feedback_matrix[tag[0]]

    def _get_tags_by_feedback(self):
        self._transform_feedback()
        tags = models.Tag.objects.filter(cluster__id=self.feedback+1)
        self.tags = [(tag.id-1, tag.name) for tag in tags]
    
    def _update_params_into_redis(self):
        print "パラメータの更新"
        common.update_redis_key(self.r, "W_" + self.user, self.W)

    def _get_bound_songs(self):
        """
        _get_bound_songsをオーバーライド
        その印象に関するフィードバックの回数を取得して減衰定数を決定する
        減衰定数と境界パラメータを用いてkを動的に決定する
        他の値についても近いものを選ぶ
        """
        top_song_objs = models.SearchMusicCluster.objects.filter(song_id=int(self.top_song)).values()
        top_song_obj = top_song_objs[0]
        emotion_value = top_song_objs[0][emotion_map[self.feedback]]
        self._decision_bound()
        print self.feedback
        self.bound_songs, self.bound_song_tag_map = common.get_bound_with_attenuation_song_tag_map(self.feedback, top_song_obj, emotion_value, self.plus_or_minus, self.bound)
        print self.bound
        print len(self.bound_songs)

    def _decision_bound(self):
        """
        boundの決定
        """
        user_feedbacks = models.EmotionEmotionbasedSong.objects.filter(user_id=int(self.user)).values()
        count = len(user_feedbacks)
        #self.bound = bound_map[self.feedback] / pow(2, count-1)
        self.bound = bound_map[self.feedback] / math.exp(-(count-1))
