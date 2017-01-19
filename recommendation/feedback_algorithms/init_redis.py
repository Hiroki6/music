# -*- coding:utf^8 -*-

import numpy as np
import redis_functions as redis_f
from .. import models
import random

feedback_map = {"relevant": 2, "emotion": 3}
"""
モデルの初期化(各ユーザーごとのモデル配列の作成・保存)
relevantなら2
emotionなら3

relevantのパラメータ: Wとbias
emotionのパラメータ: Wのみ
"""
class InitRedis(object):

    def __init__(self, seed=20, init_stdev=0.0001, feedback_type = "relevant"):
        self.seed = seed
        self.init_stdev = 0.01
        self.N = 43
        self.r = redis_f.get_redis_obj("localhost", 6379, feedback_map[feedback_type])
        self.feedback_type = feedback_type

    def init_all_user_model(self):
        """
        feedback_typeによって初期化するモデルを分ける
        """
        uniq_users = models.Preference.objects.all().values_list("user", flat=True).order_by("user").distinct()
        self.flush_db()
        for user in uniq_users:
            self.init_user_model(str(user))
    
    def update_user_model(self, user):
        """
        ユーザーの更新
        """
        redis_f.delete_redis_key(self.r, "W_" + user)
        self.init_user_model(user)

    def init_user_model(self, user):
        """
        特定のユーザーのモデル更新
        """
        if self.feedback_type == "relevant":
            self.create_and_save_user_relevant_model(user)
        else:
            self.create_and_save_user_emotion_model(user)

    def create_and_save_user_relevant_model(self, user):
        """
        relevantモデルの初期化と保存
        """
        W, bias = self.create_relevant_model()
        self.save_user_relevant_into_redis(user, W, bias)
    
    def create_and_save_user_emotion_model(self, user):
        """
        emotionモデルの初期化と保存
        """
        W = self.create_emotion_model()
        self.save_user_emotion_into_redis(user, W)

    def create_relevant_model(self):
        """
        適合性フィードバック用のモデルの作成
        """
        seed = random.randint(20, 40)
        np.random.seed(seed=seed)
        W = np.random.normal(loc=0.0, scale=self.init_stdev, size=(self.N))
        bias = 0.0
        return W, bias
    
    def create_emotion_model(self):
        """
        印象語フィードバック用のモデルの作成
        """
        seed = random.randint(20, 40)
        np.random.seed(seed=self.seed)
        W = np.random.normal(loc=0.0, scale=self.init_stdev, size=(self.N))
        return W

    def save_user_relevant_into_redis(self, user, W, bias):
        """
        特定のユーザーの適合性フィードバック用のモデルのredisへの保存
        """
        redis_f.save_one_dim_array(self.r, "W_" + user, W)
        redis_f.save_scalar(self.r, "bias", user, bias)

    def save_user_emotion_into_redis(self, user, W):
        """
        印象語フィードバック用のモデルのredisへの保存
        """
        redis_f.save_one_dim_array(self.r, "W_" + user, W)

    def flush_db(self):
        """
        dbを削除
        """
        self.r.flushdb()
