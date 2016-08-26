# -*- coding:utf-8 -*-

import math
import random
import time
import numpy as np
cimport numpy as np
cimport cython
from libc.math cimport pow, sqrt
import redis

np.import_array()

ctypedef np.float64_t DOUBLE
ctypedef np.int64_t INTEGER

cdef class CySmoothing:
    """
    paramters
    s_W: 重み配列
    s_w0: バイアス
    W_train: Wの教師パラメータ配列
    V_train: Vの教師パラメータ配列
    param_dim: 学習対象パラメータ数(K + 1)
    learned_song_tag_map: 学習された楽曲
    l_rate: 学習係数
    """
    cdef:
        np.ndarray s_W
        np.ndarray s_w0
        np.ndarray W_train
        np.ndarray V_train
        int param_dim
        dict learned_song_tag_map
        double all_error
        np.ndarray target_params
        double l_rate
        double beta

    def __cinit__(self,
            np.ndarray[DOUBLE, ndim = 2, mode="c"] s_W,
            np.ndarray[DOUBLE, ndim = 1, mode="c"] s_w0,
            np.ndarray[DOUBLE, ndim = 1, mode="c"] W_train,
            np.ndarray[DOUBLE, ndim = 2, mode="c"] V_train,
            int param_dim,
            dict learned_song_tag_map):
        self.s_W = s_W
        self.s_w0 = s_w0
        self.W_train = W_train
        self.V_train = V_train
        self.param_dim = param_dim
        self.learned_song_tag_map = learned_song_tag_map

    def learning(self, double l_rate, double beta):
        """
        全てのパラメータについて学習
        """
        cdef:
            int index

        self.l_rate = l_rate
        self.beta = beta
        for index in xrange(self.param_dim):
            # 対象ベクトル取得
            if index == 0:
                self.target_params = self.W_train
            else:
                self.target_params = np.transpose(self.V_train)[index-1]
            # 各ベクトル収束するまで学習
            self.repeat_optimization(index)

    def repeat_optimization(self, int index):
        """
        各パラメータの学習
        """
        cdef:
            int step = 100
            double before_error

        self.calc_errors(index)
        print index
        print self.all_error
        for i in xrange(step):
            self.update(index)
            before_error = self.all_error
            self.calc_errors(index)
            print self.all_error
            if self.all_error < 1 or before_error - self.all_error < 0.0001:
                break

    def update(self, int index):
        """
        パラメータの更新
        """
        cdef:
            long song_index
            np.ndarray song_tags
            double predict_value
            double error

        for song_index, song_tags in self.learned_song_tag_map.items():
            predict_value = self.predict(index, song_tags)
            error = self.target_params[song_index] - predict_value
            self.s_w0[index] += self.l_rate * error
            for tag_index, tag_value in enumerate(song_tags):
                self.s_W[index][tag_index] += 2 * self.l_rate * (error * tag_value - self.beta * self.s_W[index][tag_index])

    def calc_errors(self, int index):
        """
        損失関数の計算
        target_params: 対象のパラメータ配列
        """
        cdef:
            long song_index
            np.ndarray song_tags
            double error
            double all_error
            double predict_value
    
        all_error = 0.0
        for song_index, song_tags in self.learned_song_tag_map.items():
            predict_value = self.predict(index, song_tags)
            error = self.target_params[song_index] - predict_value
            all_error += pow(error, 2)

        self.all_error = all_error + self.beta * (np.linalg.norm(self.s_W))
        #self.all_error = all_error

    cdef double predict(self, int index, np.ndarray song_tags):

        return np.dot(self.s_W[index], song_tags) + self.s_w0[index]

    def regression_all_params(self, np.ndarray[DOUBLE, ndim=1, mode="c"] song_tags):
        """
        その楽曲のWとVの全ての次元の予測を行う
        @returns(W, V)
        """
        cdef:
            double w
            np.ndarray V

        w = self.regression_w(song_tags)
        V = self.regression_V(song_tags)

        return w, V

    cdef double regression_w(self, np.ndarray[DOUBLE, ndim=1, mode="c"] song_tags):

        return self.predict(0, song_tags)

    cdef np.ndarray regression_V(self, np.ndarray[DOUBLE, ndim=1, mode="c"] song_tags):

        cdef:
            np.ndarray V = np.zeros(self.param_dim-1)
            int i

        for i in xrange(self.param_dim-1):
            V[i] = self.predict(i+1, song_tags)

        return V
