# -*- coding:utf^8 -*-

import numpy as np

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
        self.DB = feedback_map[feedback_type]
        self.HOST = "localhost"
        self.PORT = 6379
        self.N = 43

    """
    適合性フィードバック用のモデルの作成
    """
    def create_relevant_model(self):
        np.random.seed(seed=self.seed)
        W = np.random.normal(scale=init_stdev,size=(N))
        bias = 0.0
        return
    
    """
    印象語フィードバック用のモデルの作成
    """
    def create_emotion_model(self):
        return

    """
    適合性フィードバック用のモデルのredisへの保存
    """
    def save_relevant_into_redis(self):
        return

    """
    印象語フィードバック用のモデルのredisへの保存
    """
    def save_emotion_into_redis(self):
        return

