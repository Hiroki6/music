# -*- coding:utf-8 -*-

"""
印象語検索における適合性フィードバックによるモデルの学習
"""

import numpy as np
import redis
import common_functions as common
from RelevantFeedback import cy_relevant_feedback as cy_rf
import sys
from recommendation.models import EmotionRelevantSong

HOST = 'localhost'
PORT = 6379
DB = 2

class RelevantFeedback:
    """
    適合性フィードバックによるオンライン学習クラス
    """
    def __init__(self, user, emotion):
        self.user = user
        self._get_params_by_redis()
        self.emotion = emotion
        self._get_learning_data()
        self.cy_obj = cy_rf.CyRelevantFeedback(self.W, self.bias, 43)

    def _get_params_by_redis(self):
        self.r = common.get_redis_obj(HOST, PORT, DB)
        key =  "W_" + self.user
        self.W = common.get_one_dim_params(self.r, key)
        self.bias = common.get_scalar(self.r, "bias", self.user)

    def _get_learning_data(self):
        """
        学習データの取得
        """
        relevant_datas = EmotionRelevantSong.objects.filter(user_id=int(self.user)).values()
        self.song_relevant = {} # {song_id: relevant_type}
        for relevant_data in relevant_datas:
            self.song_relevant[relevant_data["song_id"]] = relevant_data["relevant_type"]

    def set_learning_params(self, l_rate, beta):
        """
        学習パラメータの設定
        """
        self.cy_obj.set_learning_params(l_rate, beta)
        self.set_listening_songs()

    def set_listening_songs(self):

        self.songs, self.song_tag_map = common.get_listening_songs(self.user)

    def fit(self):
        """
        CyRelevantFeedbackクラスを用いたモデルの学習
        """
        for i in xrange(100):
            for song_id, relevant_type in self.song_relevant.items():
                self.cy_obj.fit(self.song_tag_map[song_id], relevant_type)
            error = self._calc_all_error()
            print error
            if error < 0.01:
                break

    def _calc_all_error(self):

        error = 0.0
        for song_id, relevant_type in self.song_relevant.items():
            error += self.cy_obj.calc_error(self.song_tag_map[song_id], relevant_type)

        return error

    def get_top_k_songs(self, k=1):
        """
        検索対象の印象語に含まれている楽曲から回帰値の高いk個の楽曲を取得する
        """
        songs, song_tag_map = common.get_not_listening_songs(self.user, self.emotion)
        top_song = 0
        top_song_value = -sys.maxint
        rankings = [(self.cy_obj.predict(tags), song_id) for song_id, tags in song_tag_map.items()]
        common.listtuple_sort_reverse(rankings)
        return rankings[:k]
