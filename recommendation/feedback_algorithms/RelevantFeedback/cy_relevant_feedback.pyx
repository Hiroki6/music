# -*- coding:utf-8 -*-

from libc.math cimport pow, sqrt
import math
import random
import time
import numpy as np
cimport numpy as np
cimport cython
import redis

np.import_array()

ctypedef np.float64_t DOUBLE
ctypedef np.int64_t INTEGER

cdef class CyRelevantFeedback:
    """
    W: 重み行列
    bias: バイアス
    feature_num: 特徴量の総数
    l_rate: 学習係数
    beta: 正規化係数
    error: 学習誤差
    """
    cdef:
        np.ndarray W
        double bias
        int feature_num
        double l_rate
        double beta
        double error
        
    def __cinit__(self,
            np.ndarray[DOUBLE, ndim=1, mode="c"] W,
            double bias,
            int feature_num):
        self.W = W
        self.bias = bias
        self.feature_num = feature_num

    def predict(self, np.ndarray[DOUBLE, ndim=1, mode="c"] X):
        """
        特徴ベクトルXに対する回帰予測
        """
        return np.dot(self.W, X) + self.bias

    def calc_error(self, np.ndarray[DOUBLE, ndim=1, mode="c"] X, double target):
        """
        回帰誤差計算
        """
        return target - self.predict(X)

    def set_learning_params(self, double l_rate, double beta):
        self.l_rate = l_rate
        self.beta = beta

    def fit(self, np.ndarray[DOUBLE, ndim=1, mode="c"] X, int relevant_type):
        
        self.error = self.calc_error(X, relevant_type)
        self._update_bias()
        self._update_W(X)

    cdef void _update_bias(self):

        self.bias += 2 * self.l_rate * (self.error)

    cdef void _update_W(self, np.ndarray[DOUBLE, ndim=1, mode="c"] X):
        
        cdef:
            int index

        for index in xrange(self.feature_num):
            self.W[index] += 2 * self.l_rate * (self.error * X[index] - self.beta * self.W[index])

    def get_bias(self):
        return self.bias
