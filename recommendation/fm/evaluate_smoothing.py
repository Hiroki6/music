# -*- coding:utf-8 -*-

import numpy as np
import redis
from math import sqrt

class EvaluationSmoothing():

    def __init__(self, K):
        self.K = K
        self.get_redis_obj()
        self.get_params()
        self.get_labels()
        self.get_validation_songs()

    def get_redis_obj(self):

        self.r_train = redis.Redis(host="localhost", port=6379, db=0)
        self.r_validation = redis.Redis(host="localhost", port=6379, db=1)

    def get_params(self):

        self.get_W()
        self.get_V(len(self.W_train))

    def get_W(self):

        W_train = self.r_train.lrange("W", 0, -1)
        W_validation = self.r_validation.lrange("W", 0, -1)
        self.W_train = self.change_array_into_float(W_train)
        self.W_validation = self.change_array_into_float(W_validation)

    def change_array_into_float(self, params):

        return np.array(params, dtype=np.float64)

    def get_V(self, n):

        self.V_train = self.get_two_dim_by_redis(self.r_train, "V_", n)
        self.V_validation = self.get_two_dim_by_redis(self.r_validation, "V_", n)

    def get_two_dim_by_redis(self, redis_obj, pre_key, n):

        V = np.ones((self.K, n))
        for i in xrange(self.K):
            key = pre_key + str(i)
            v = redis_obj.lrange(key, 0, -1)
            V[i] = v
        V = np.array(V, dtype=np.float64)
        return V.T.copy(order='C')

    def evaluation(self):
        
        self.W_evaluation()
        self.V_evaluation()

    """
    WについてRMSEを計測する
    """
    def W_evaluation(self):
        
        rmse = np.sum((self.W_train - self.W_validation)**2)
        self.rmse_w = sqrt(rmse/len(self.validation_songs))

    """
    VについてRMSEを計測する
    """
    def V_evaluation(self):
    
        rmse = 0
        for song in self.validation_songs:
            song_index = self.labels["song=" + song]
            rmse = np.sum((self.V_train[song_index] - self.V_validation[song_index]) ** 2)
        self.rmse_v = sqrt(rmse/len(self.validation_songs))
        
    def get_labels(self):
    
        self.labels = {}
        keys = self.r_train.lrange("label_keys", 0, -1)
        values = self.r_train.lrange("label_values", 0, -1)
        values = np.array(values, dtype=np.int)
        for key, value in zip(keys, values):
            self.labels[key] = value

    def get_validation_songs(self):

        self.validation_songs = self.r_validation.lrange("validation_songs", 0, -1)
        #self.validation_songs = map(int, validation_songs)
