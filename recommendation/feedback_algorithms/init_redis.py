# -*- coding:utf^8 -*-

import numpy as np
import common_functions as common
from .. import models

feedback_map = {"relevant": 2, "emotion": 3}
"""
モデルの初期化(各ユーザーごとのモデル配列の作成・保存)
relevantなら2
emotionなら3
"""
class InitRedis(object):

    def __init__(self, seed=20, init_stdev=0.01, feedback_type = "relevant"):
        self.seed = seed
        self.init_stdev = 0.01
        self.N = 43
        self.r = common.get_redis_obj("localhost", 6379, feedback_map[feedback_type])

    def init_all_user_relevant_model(self):

        uniq_users = models.Preference.objects.all().values_list("user", flat=True).order_by("user").distinct()
        for user in uniq_users:
            self.create_and_save_relevant_model(str(user))

    def create_and_save_relevant_model(self, user):

        W, bias = self.create_relevant_model()
        self.save_relevant_into_redis(user, W, bias)

    def create_relevant_model(self):
        """
        適合性フィードバック用のモデルの作成
        """
        np.random.seed(seed=self.seed)
        W = np.random.normal(scale=self.init_stdev,size=(self.N))
        bias = 0.0
        return W, bias
    
    def create_emotion_model(self):
        """
        印象語フィードバック用のモデルの作成
        """
        return

    def save_relevant_into_redis(self, user, W, bias):
        """
        適合性フィードバック用のモデルのredisへの保存
        """
        common.save_one_dim_array(self.r, "W_" + user, W)
        common.save_scala(self.r, "bias", user, bias)

    def save_emotion_into_redis(self):
        """
        印象語フィードバック用のモデルのredisへの保存
        """
        return
