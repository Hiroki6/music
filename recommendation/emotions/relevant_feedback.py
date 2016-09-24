# -*- coding:utf-8 -*-

"""
印象語検索における適合性フィードバックによるモデルの学習
"""

import numpy as np
import redis

HOST = 'localhost'
PORT = 6379
DB = 2

class RelevantFeedback:

    def __init__(self):
        self._get_params_by_redis()

    def _get_params_by_redis(self):
        return

    def learning(self):
        return
