# -*- coding:utf-8 -*-

"""
印象語検索における適合性フィードバックによるモデルの学習
"""

import numpy as np
import redis
import common_functions as common
from RelevantFeedback import cy_relevant_feedback as cy_rf
import sys

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
        self.cy_obj = cy_rf.CyRelevantFeedback(self.W, self.bias)

    def _get_params_by_redis(self):
        self.r = common.get_redis_obj(HOST, PORT, DB)
        key =  "W_" + self.user
        self.W = common.get_one_dim_params(self.r, key)
        self.bias = common.get_scalar(self.r, "bias", self.user)

    def learning(self):
        return

    def get_recommend_songs(self, k=1):
        """
        検索対象の印象語に含まれている楽曲から回帰値の高いk個の楽曲を取得する
        """
        songs, song_tag_map = common.get_not_listening_songs(self.user, self.emotion)
        top_song = 0
        top_song_value = -sys.maxint
        for song, tags in song_tag_map.items():
            tags = np.array(tags)
            value = self.cy_obj.predict(tags)
            if value > top_song_value:
                top_song = song
                top_song_value = value

        return top_song

    def save_song_and_tags(self, song, tags):
        return
