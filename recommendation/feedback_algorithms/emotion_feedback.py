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
        self._get_params_by_redis()

    def _get_params_by_redis(self):
        self.r = common.get_redis_obj(HOST, PORT, DB)
        key =  "W_" + self.user
        self.top_song = common.get_scalar(self.r, "top_song", self.user)
        self.top_matrix = common.get_one_dim_params(self.r, "top_matrix_"+self.user)
        self.W = common.get_one_dim_params(self.r, key)

    def save_top_song(self):
        common.save_scale(self.r, "top_song", self.user, "")
        common.save_one_dim_array(self.r, "top_matrix_"+self.user, "")

    def create_feedback_matrix(self, feedback):
        """
        特定のユーザーによるフィードバックを反映させた楽曲の特徴ベクトル生成
        top_matrix: 推薦された楽曲配列
        feedback_matrix: フィードバックを受けたタグの部分だけ値を大きくしたもの
        """
        self.get_tags_by_feedback(feedback)
        self.feedback_matrix = self.top_matrix.copy()
        alpha = 0.1 if self.plus_or_minus == 1 else -0.1 # フィードバックによって+-を分ける
        for tag in enumerate(self.tags):
            self.feedback_matrix[tag[0]] += alpha/self.feedback_matrix[tag[0]]

    def get_tags_by_feedback(self, feedback):
        """
        feedback: 1~10
        """
        feedback = int(feedback)
        if(feedback <= 4):
            self.plus_or_minus = 1
        else:
            self.plus_or_minus = -1
            feedback -= 5
        feedback += 1
        tags = models.Tag.objects.filter(cluster__id=feedback)
        self.tags = [(tag.id-1, tag.name) for tag in tags]

