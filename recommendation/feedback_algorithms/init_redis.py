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
        self.feedback_type = feedback_type

    def init_all_user_model(self):
        """
        feedback_typeによって初期化するモデルを分ける
        """
        if self.feedback_type == "relevant":
            self.init_all_user_relevant_model()
        else:
            return

    def init_all_user_relevant_model(self):
        """
        relevantモデル全て初期化
        """
        uniq_users = models.Preference.objects.all().values_list("user", flat=True).order_by("user").distinct()
        self.flush_db()
        for user in uniq_users:
            self.create_and_save_user_relevant_model(str(user))

    def init_user_model(self, user):
        """
        特定のユーザーのモデル
        """
        if self.feedback_type == "relevant":
            self.init_user_relevant_model(user)
        else:
            return

    def init_user_relevant_model(self, user):
        """
        特定のユーザーのrelevantモデル更新
        """
        common.delete_redis_key(self.r, "W_" + user)
        self.create_and_save_user_relevant_model(user)

    def create_and_save_user_relevant_model(self, user):
        """
        relevantモデルの初期化と保存
        """
        W, bias = self.create_relevant_model()
        self.save_user_relevant_into_redis(user, W, bias)

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

    def save_user_relevant_into_redis(self, user, W, bias):
        """
        特定のユーザーの適合性フィードバック用のモデルのredisへの保存
        """
        common.save_one_dim_array(self.r, "W_" + user, W)
        common.save_scalar(self.r, "bias", user, bias)

    def save_emotion_into_redis(self):
        """
        印象語フィードバック用のモデルのredisへの保存
        """
        return

    def flush_db(self):
        """
        dbを削除
        """
        self.r.flushdb()
