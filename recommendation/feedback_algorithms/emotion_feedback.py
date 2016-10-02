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

HOST = 'localhost'
PORT = 6379
DB = 3

class EmotionFeedback:
    """
    印象語フィードバックによるオンライン学習クラス
    """
    def __init__(self, user, emotion):
        self.user = user
        self.emotion = emotion
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

    def fit(self):
        """
        学習
        """
        print "学習開始"
        X = self.feedback_matrix - self.top_matrix
        self.cy_obj.fit(X)
        self._update_params_into_redis()
 
    def get_top_k_songs(self, k=1):
        """
        検索対象の印象語に含まれている楽曲から回帰値の高いk個の楽曲を取得する
        """
        songs, song_tag_map = common.get_not_listening_songs(self.user, self.emotion, "emotion")
        rankings = [(self.cy_obj.predict(tags), song_id) for song_id, tags in song_tag_map.items()]
        common.listtuple_sort_reverse(rankings)
        self.top_song = rankings[0][1]
        self.top_matrix = song_tag_map[self.top_song]
        self.save_top_song()
        common.write_top_k_songs(rankings[:10])
        return rankings[:k]

    def save_top_song(self):
        common.delete_redis_key(self.r, "top_matrix_" + self.user)
        common.save_scalar(self.r, "top_song", self.user, self.top_song)
        common.save_one_dim_array(self.r, "top_matrix_"+self.user, self.top_matrix)

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

    def _get_last_feedback(self):
        """
        最後のフィードバック情報取得
        """
        emotion_datas = models.EmotionEmotionbasedSong.objects.order_by("id").filter(user_id=int(self.user)).values()
        emotion_datas = emotion_datas.reverse()
        self.feedback = emotion_datas[0]["feedback_type"]

    def _get_tags_by_feedback(self):
        """
        feedback: 1~10
        """
        if(self.feedback <= 4):
            self.plus_or_minus = 1
        else:
            self.plus_or_minus = -1
            self.feedback -= 5
        self.feedback += 1
        tags = models.Tag.objects.filter(cluster__id=self.feedback)
        self.tags = [(tag.id-1, tag.name) for tag in tags]
    
    def _get_last_song(self):
        self.top_song = common.get_scalar(self.r, "top_song", self.user)
        self.top_matrix = common.get_one_dim_params(self.r, "top_matrix_"+self.user)

    def _update_params_into_redis(self):
        print "パラメータの更新"
        common.update_redis_key(self.r, "W_" + self.user, self.W)

