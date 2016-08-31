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
    K: 学習対象パラメータ数(K + 1)
    learned_song_tag_map: 学習された楽曲
    l_rate: 学習係数
    """
    cdef:
        np.ndarray s_W
        np.ndarray s_V
        double s_w0
        np.ndarray s_v0
        np.ndarray W_train
        np.ndarray V_train
        int K
        dict learned_song_tag_map
        double all_error
        np.ndarray target_params
        double l_rate
        double beta
        np.ndarray regs

    def __cinit__(self,
            np.ndarray[DOUBLE, ndim = 1, mode="c"] s_W,
            np.ndarray[DOUBLE, ndim = 2, mode="c"] s_V,
            double s_w0,
            np.ndarray[DOUBLE, ndim = 1, mode="c"] s_v0,
            np.ndarray[DOUBLE, ndim = 1, mode="c"] W_train,
            np.ndarray[DOUBLE, ndim = 2, mode="c"] V_train,
            int K,
            dict learned_song_tag_map):
        self.s_W = s_W
        self.s_V = s_V
        self.s_w0 = s_w0
        self.s_v0 = s_v0
        self.W_train = W_train
        self.V_train = V_train
        self.K = K
        self.learned_song_tag_map = learned_song_tag_map

    def learning(self, double w_rate, double v_rate, double beta):
        """
        全てのパラメータについて学習
        """
        cdef:
            int index

        self.beta = beta
        self.regs = np.zeros(self.K+1)
        for index in xrange(self.K+1):
            # 対象ベクトル取得
            if index == 0:
                self.target_params = self.W_train
                self.l_rate = w_rate
            else:
                self.target_params = np.transpose(self.V_train)[index-1]
                self.l_rate = v_rate
            # 各ベクトル収束するまで学習
            self.repeat_optimization(index)

    def repeat_optimization(self, int index):
        """
        各パラメータの学習
        """
        cdef:
            int step = 100
            double before_error

        self._calc_errors(index)
        print index
        print self.all_error
        for i in xrange(step):
            if index == 0:
                self._update_W()
            else:
                self._update_V(index)
            #self.update(index)
            before_error = self.all_error
            self._calc_errors(index)
            print self.all_error
            if self.all_error < 0.1 or abs(before_error - self.all_error) < 0.0001:
                break

    def _update_W(self):
        """
        パラメータの更新
        """
        cdef:
            long song_index
            np.ndarray song_tags
            double predict_value
            double error
            int tag_index
            double tag_value
            np.ndarray pre_s_W

        for song_index, song_tags in self.learned_song_tag_map.items():
            predict_value = self._predict(0, song_tags)
            error = self.target_params[song_index] - predict_value
            self.s_w0 += self.l_rate * error
            pre_s_W = self.s_W
            for tag_index, tag_value in enumerate(song_tags):
                #self.s_W[tag_index] += 2 * self.l_rate * (error * tag_value - self.regs[0] * self.s_W[tag_index])
                self.s_W[tag_index] += 2 * self.l_rate * (error * tag_value - self.beta * self.s_W[tag_index])
            #self._calc_regs(pre_s_W, 0)

    def _update_V(self, int index):
        """
        パラメータの更新
        """
        cdef:
            long song_index
            np.ndarray song_tags
            double predict_value
            double error
            int tag_index
            double tag_value
            np.ndarray pre_s_V
            int v_index = index - 1

        for song_index, song_tags in self.learned_song_tag_map.items():
            predict_value = self._predict(index, song_tags)
            error = self.target_params[song_index] - predict_value
            self.s_v0[v_index] += self.l_rate * error
            pre_s_V = self.s_V[v_index]
            for tag_index, tag_value in enumerate(song_tags):
                #self.s_V[v_index][tag_index] += 2 * self.l_rate * (error * tag_value - self.regs[index] * self.s_V[v_index][tag_index])
                self.s_V[v_index][tag_index] += 2 * self.l_rate * (error * tag_value - self.beta * self.s_V[v_index][tag_index])
            #self._calc_regs(pre_s_V, index)

    cdef void _calc_regs(self, np.ndarray[DOUBLE, ndim=1, mode="c"] pre_params, int index):

        cdef:
            double new_r
            np.ndarray song_tags
            double err
            long song_index

        (song_index, song_tags) = random.choice(self.learned_song_tag_map.items())
        err = -2 * self._predict(index, song_tags)
        new_r = self.regs[index] - self.l_rate * (err * -2 * self.l_rate * np.dot(pre_params, song_tags))
        self.regs[index] = new_r if new_r >= 0 else 0

    def _calc_errors(self, int index):
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
            double regs_sum = 0.0
    
        all_error = 0.0
        for song_index, song_tags in self.learned_song_tag_map.items():
            predict_value = self._predict(index, song_tags)
            error = self.target_params[song_index] - predict_value
            all_error += pow(error, 2)
        
        if index == 0:
            #regs_sum = self.regs[index] * np.sum(self.s_W ** 2)
            regs_sum = self.beta * np.sum(self.s_W ** 2)
        else:
            #regs_sum = self.regs[index] * np.sum(self.s_V[index-1] ** 2)
            regs_sum = self.beta * np.sum(self.s_V[index-1] ** 2)

        self.all_error = all_error + regs_sum

    cdef double _predict(self, int index, np.ndarray song_tags):
        
        if index == 0:
            return np.dot(self.s_W, song_tags) + self.s_w0
        else:
            return np.dot(self.s_V[index-1], song_tags) + self.s_v0[index-1]

    def regression_all_params(self, np.ndarray[DOUBLE, ndim=1, mode="c"] song_tags):
        """
        その楽曲のWとVの全ての次元の予測を行う
        @returns(W, V)
        """
        cdef:
            double w
            np.ndarray V

        w = self._regression_w(song_tags)
        V = self._regression_V(song_tags)

        return w, V

    cdef double _regression_w(self, np.ndarray[DOUBLE, ndim=1, mode="c"] song_tags):

        return self._predict(0, song_tags)

    cdef np.ndarray _regression_V(self, np.ndarray[DOUBLE, ndim=1, mode="c"] song_tags):

        cdef:
            np.ndarray V = np.zeros(self.K)
            int i

        for i in xrange(self.K):
            V[i] = self._predict(i+1, song_tags)

        return V
