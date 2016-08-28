# -*- coding:utf-8 -*-

import numpy as np
import redis
from math import sqrt

class EvaluationSmoothing():
    """
    parameters
    K: Vの次元
    W_train: 学習済みのW配列
    W_validation: 交差検定により予測されたW配列
    V_train: 学習済みのV配列
    V_validation: 交差検定により予測されたV配列
    rmse_w: WのRMSE
    rmse_v: VのRMSE
    """
    def __init__(self, K):
        self.K = K
        self.get_redis_obj()
        self.get_params()
        self.get_validation_song_indexes()

    def get_redis_obj(self):

        self.r = redis.Redis(host="localhost", port=6379, db=1)

    def get_params(self):

        self.get_W()
        self.get_V(len(self.W_train))

    def get_W(self):

        W_train = self.r.lrange("W", 0, -1)
        W_validation = self.r.lrange("W_s", 0, -1)
        self.W_train = self.change_array_into_float(W_train)
        self.W_validation = self.change_array_into_float(W_validation)

    def change_array_into_float(self, params):

        return np.array(params, dtype=np.float64)

    def get_V(self, n):

        self.V_train = self.get_two_dim_by_redis(self.r, "V_", n)
        self.V_validation = self.get_two_dim_by_redis(self.r, "V_s_", n)

    def get_two_dim_by_redis(self, redis_obj, pre_key, n):

        V = np.ones((self.K, n))
        for i in xrange(self.K):
            key = pre_key + str(i)
            v = redis_obj.lrange(key, 0, -1)
            V[i] = v
        V = np.array(V, dtype=np.float64)
        return V.T.copy(order='C')

    def evaluation(self):
        
        rmse_w = 0
        rmse_v = 0
        mae_w = 0
        mae_v = 0
        count = 0
        for index in self.indexes:
            if self.W_train[index] != 0.0:
                rmse_w += pow(self.W_train[index] - self.W_validation[index], 2)
                rmse_v += np.sum((self.V_train[index] - self.V_validation[index]) ** 2)/self.K
                mae_w += abs(self.W_train[index] - self.W_validation[index])
                mae_v += np.sum(abs(self.V_train[index] - self.V_validation[index]))/self.K
                count += 1
        self.rmse_w = sqrt(rmse_w/count)
        self.rmse_v = sqrt(rmse_v/count)
        self.mae_w = mae_w / count
        self.mae_v = mae_v / count

    def get_validation_song_indexes(self):

        indexes = self.r.lrange("smoothing_songs", 0, -1)
        self.indexes = map(int, indexes)
