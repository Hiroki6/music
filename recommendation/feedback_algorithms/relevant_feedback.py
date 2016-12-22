# -*- coding:utf-8 -*-

"""
印象語検索における適合性フィードバックによるモデルの学習
"""

import numpy as np
import redis
import common_functions as common
from RelevantFeedback import cy_relevant_feedback as cy_rf
import sys
from recommendation import models
import codecs
import random

HOST = 'localhost'
PORT = 6379
DB = 2

emotion_map = {1: "pop", 2: "ballad", 3: "rock"}

class RelevantFeedback:
    """
    適合性フィードバックによるオンライン学習クラス
    """
    def __init__(self, user, emotions):
        self.user = user
        self._get_params_by_redis()
        self.emotions = emotions
        self.cy_obj = cy_rf.CyRelevantFeedback(self.W, self.bias, 43)

    def _get_params_by_redis(self):
        self.r = common.get_redis_obj(HOST, PORT, DB)
        key =  "W_" + self.user
        self.W = common.get_one_dim_params(self.r, key)
        self.bias = common.get_scalar(self.r, "bias", self.user)

    def _get_learning_data(self, learning_method):
        """
        学習データの取得
        """
        relevant_datas = models.EmotionRelevantSong.objects.order_by("id").filter(user_id=int(self.user)).values()
        self.song_relevant = {} # {song_id: relevant_type}
        if learning_method == "online":
            relevant_datas = relevant_datas.reverse()
            self.song_relevant[relevant_datas[0]["song_id"]] = relevant_datas[0]["relevant_type"]
        else:
            for relevant_data in relevant_datas:
                self.song_relevant[relevant_data["song_id"]] = relevant_data["relevant_type"]

    def set_learning_params(self, l_rate, beta, learning_method = "online"):
        """
        学習パラメータの設定
        """
        self.beta = beta
        self.cy_obj.set_learning_params(l_rate, beta)
        self._get_learning_data(learning_method)
        self._set_listening_songs()

    def _set_listening_songs(self):

        self.songs, self.song_tag_map = common.get_listening_songs(self.user)

    def fit(self):
        """
        CyRelevantFeedbackクラスを用いたモデルの学習
        """
        error = 0
        for i in xrange(10000):
            before_error = error
            #for song_id, relevant_type in self.song_relevant.items():
            #    self.cy_obj.fit(self.song_tag_map[song_id], relevant_type)
            song_id = random.choice(self.song_relevant.keys())
            relevant_type = self.song_relevant[song_id]
            if relevant_type == 0:
                continue
            self.cy_obj.fit(self.song_tag_map[song_id], relevant_type)
            error = self._calc_all_error()
            if error < 0.0001 or abs(error - before_error) < 0.000001:
                print "iterations %d" % (i)
                print "final error %.8f" % (error)
                self.bias = self.cy_obj.get_bias()
                break
        for song_id, relevant_type in self.song_relevant.items():
            if relevant_type == 0:
                continue
            print "target: %.1f" % (relevant_type)
            print "predict: %.8f" % (self.cy_obj.predict(self.song_tag_map[song_id]))
        self._update_params_into_redis()

    def _calc_all_error(self):

        error = 0.0
        for song_id, relevant_type in self.song_relevant.items():
            error += pow(self.cy_obj.calc_error(self.song_tag_map[song_id], relevant_type), 2)
        error += self.beta * np.linalg.norm(self.W)

        return error

    def get_top_k_songs(self, init_flag = False, k=1):
        """
        検索対象の印象語に含まれている楽曲から回帰値の高いk個の楽曲を取得する
        """
        #songs, song_tag_map = common.get_not_listening_songs(self.user, self.emotions)
        # 初期検索の時
        song_cluster_map = common.get_song_and_cluster()
        if init_flag:
            pass
        else:
            songs, song_tag_map = common.get_not_listening_songs_by_multi_emotion(self.user, self.emotions)
            rankings = [(self.cy_obj.predict(tags)*song_cluster_map[song_id][emotion_map[int(self.emotions[0])]], song_id) for song_id, tags in song_tag_map.items()]
            common.listtuple_sort_reverse(rankings)
            common.write_top_k_songs(self.user, "relevant_k_song.txt", rankings[:10], self.emotions)
        return rankings[:k]

    def _update_params_into_redis(self):
        common.update_redis_key(self.r, "W_" + self.user, self.W)
        common.save_scalar(self.r, "bias", self.user, self.bias)
