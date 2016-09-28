# -*- coding:utf-8 -*-

"""
印象語検索における印象語フィードバックによるモデルの学習
"""

import numpy as np
import redis
import common_functions as common
from EmotionFeedback import cy_emotion_feedback as cy_ef
import sys
from recommendation.models import EmotionEmotionbasedSong

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

    def _get_params_by_redis(self):
        self.r = common.get_redis_obj(HOST, PORT, DB)
        self.top_song = common.get_scalar(self.r, "top_song", self.user)
        self.top_matrix = common.get_one_dim_params(self.r, "top_matrix_"+self.user)

    def save_top_song(self):
        common.save_scale(self.r, "top_song", self.user, "")
        common.save_one_dim_array(self.r, "top_matrix_"+self.user, "")

