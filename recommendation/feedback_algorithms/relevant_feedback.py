# -*- coding:utf-8 -*-

"""
印象語検索における適合性フィードバックによるモデルの学習
"""

import numpy as np
import redis
import common_functions as common

HOST = 'localhost'
PORT = 6379
DB = 2

class RelevantFeedback:
    """
    適合性フィードバックによるオンライン学習クラス
    """
    def __init__(self, user):
        self._get_params_by_redis()
        self.user = user

    def _get_params_by_redis(self):
        self.r = common.get_redis_obj(HOST, PORT, DB)
        key =  "W_" + self.user
        self.W = common.get_one_dim_params(redis_obj, key)
        self.bias = get_scalar(redis_obj, "bias", self.user)

    def learning(self):
        return

    def get_recommend_songs(self, cluster, k):
        """
        検索対象の印象語に含まれている楽曲から回帰値の高いk個の楽曲を取得する
        """
        return
