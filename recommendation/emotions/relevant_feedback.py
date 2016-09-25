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

    def __init__(self, user):
        self._get_params_by_redis()
        self.user = user

    def _get_params_by_redis(self):
        self._set_redis_obj()
        key =  "W_" + self.user
        self.W = common.get_one_dim_params(redis_obj, key)
        self.bias = get_scalar(redis_obj, "bias", self.user)

    def _set_redis_obj(self):
        self.r = redis.Redis(host=HOST, port=PORT, db=DB)

    def learning(self):
        return
