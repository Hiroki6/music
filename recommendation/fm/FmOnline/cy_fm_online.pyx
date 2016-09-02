# -*- coding:utf-8 -*-
"""
Factorization Machineをcythonを使って高速化
学習手法は確率的勾配法(SGD)
学習率はAdaGradを使用
正規化項は「Learning Recommender Systems with Adaptive Regularization」参考
データはオンラインで行う
"""

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

cdef class CyFmOnline:
    """
    parameters
    w_0 : バイアス 1
    W : 各特徴量の重み n
    V : 各特徴量の相互作用の重み n * K
    adagrad_w_0 : adagradにおけるw_0の保存配列 1
    adagrad_V : adagradにおけるVの保存配列 n * K
    adagrad_W : adagradにおけるWの保存配列 n
    n : 特徴量の総数
    regs : regulations 配列 K+2 (0: w_0, 1: W, 2~K+2: V)
    l_rate : 学習率
    K : Vの次元
    step : 学習ステップ数
    labels: {feature: index}
    train_data: 学習データ
    regs_data: 正規化項用データ
    """
    cdef:
        np.ndarray W
        np.ndarray V
        double w_0
        long n
        np.ndarray adagrad_W
        np.ndarray adagrad_V
        double adagrad_w_0
        np.ndarray regs
        double now_error
        double l_rate
        int K
        int step
        dict labels
        np.ndarray train_data
        np.ndarray regs_data
        np.ndarray ixs

    def __cinit__(self,
                    np.ndarray[DOUBLE, ndim=1, mode="c"] W,
                    np.ndarray[DOUBLE, ndim=2, mode="c"] V,
                    double w_0,
                    long n,
                    np.ndarray[DOUBLE, ndim=1, mode="c"] regs,
                    double l_rate,
                    int K,
                    int step,
                    dict labels):
        self.W = W
        self.V = V
        self.w_0 = w_0
        self.n = n
        self.regs = regs
        self.l_rate = l_rate
        self.K = K
        self.step = step
        self.labels = labels
        self.adagrad_w_0 = 0.0
        self.adagrad_W = np.zeros(self.n)
        self.adagrad_V = np.zeros((self.n, self.K))

    cdef void _update_w_0(self):
        """
        w_0の更新
        """
        cdef:
            double grad_value = 0.0
            double update_value = 0.0

        grad_value = 2 * self.l_rate*(self.now_error + self.regs[0]*self.w_0)
 
        self.adagrad_w_0 += grad_value * grad_value
        update_value = self.l_rate * grad_value / sqrt(self.adagrad_w_0)
        self.w_0 -= update_value

    cdef void _update_W(self, long i):
        """
        W[i]の更新
        """
        cdef:
            double grad_value = 0.0
            double update_value = 0.0

        grad_value = 2 * (self.now_error*self.train_data[i] + self.regs[1]*self.W[i])
        self.adagrad_W[i] += grad_value * grad_value
        update_value = self.l_rate * grad_value / sqrt(self.adagrad_W[i])
        self.W[i] -= update_value

    cdef void _update_V(self, long i, int f):
        """
        V[i][f]の更新
        """
        cdef:
            double grad_value = 0.0
            double update_value = 0.0
            double h = 0.0
            double h_pre = 0.0
            long ix

        for ix in self.ixs:
            h_pre += self.V[ix][f] * self.train_data[ix]
        h = h_pre - self.V[i][f]*self.train_data[i]
        h *= self.train_data[i]
        grad_value = 2 * (self.now_error*h + self.regs[f+2]*self.V[i][f])
        self.adagrad_V[i][f] += grad_value * grad_value
        update_value = self.l_rate * grad_value / sqrt(self.adagrad_V[i][f])
        self.V[i][f] -= update_value

    def fit(self, np.ndarray[DOUBLE, ndim=1, mode="c"] train_data, np.ndarray[DOUBLE, ndim=1, mode="c"] regs_data):
        
        cdef:
            long ix
            int f
            double pre_w_0
            np.ndarray[DOUBLE, ndim=1, mode="c"] pre_W
            np.ndarray[DOUBLE, ndim=2, mode="c"] pre_V

        self.train_data = train_data
        self.regs_data = regs_data
        self.ixs = np.nonzero(self.train_data)[0]
        self.now_error = self.calc_error(train_data)
        self._update_w_0()
        pre_w_0 = self.w_0
        pre_W = self.W
        pre_V = self.V
        for ix in self.ixs:
            self._update_W(ix)
            for f in xrange(self.K):
                self._update_V(ix, f)

        self._calc_regs(pre_w_0, pre_W, pre_V)

    cdef void _calc_regs(self, double pre_w_0, np.ndarray[DOUBLE, ndim=1, mode="c"] pre_W, np.ndarray[DOUBLE, ndim=2, mode="c"] pre_V):
        """
        regsの最適化
        """
        cdef:
            double new_r
            double err
            long ix
            int f
            long random_index
            double dot_r_v = 0.0
            double dot_r_v_pre = 0.0
            double dot_sum = 0.0
        
        self.ixs = np.nonzero(self.regs_data)[0]
        err = 2 * self.calc_error(self.regs_data)
        # lambda_0
        new_r = self.regs[0] - self.l_rate * (err * -2 * self.l_rate * pre_w_0)
        self.regs[0] = new_r if new_r >= 0 else 0
        # lambda_w
        new_r = self.regs[1] - self.l_rate * (err * -2 * self.l_rate * np.dot(pre_W, self.regs_data))
        self.regs[1] = new_r if new_r >= 0 else 0
        for f in xrange(self.K):
            # lambda_v_f
            dot_r_v = 0.0
            dot_r_v_pre = 0.0
            dot_sum = 0.0
            for ix in self.ixs:
                dot_r_v += self.regs_data[ix] * self.V[ix][f]
                dot_r_v_pre += self.regs_data[ix] * pre_V[ix][f]
                dot_sum += self.regs_data[ix] * self.regs_data[ix] * self.V[ix][f] * pre_V[ix][f]
            new_r = self.regs[f+2] - self.l_rate * (err * -2 * self.l_rate * dot_r_v * dot_r_v_pre - dot_sum)
            self.regs[f+2] = new_r if new_r >= 0 else 0

    def calc_error(self, np.ndarray[DOUBLE, ndim=1, mode="c"] target_data):
        return self._calc_rating(target_data, self.ixs) - 1.0

    def calc_all_regs(self):

        cdef:
            double error = 0.0
            int f

        error += self.regs[0] * pow(self.w_0, 2) + self.regs[1] * np.sum(self.W**2)
        for f in xrange(self.K):
            error += self.regs[f+2] * np.sum(np.transpose(self.V)[f]**2)

        return error

    def predict(self, np.ndarray[DOUBLE, ndim=1, mode="c"] matrix, char* song, np.ndarray[INTEGER, ndim=1, mode="c"] ixs):
        """
        python側から呼び出せる回帰予測結果取得
        """
        ixs[-1] = self.labels["song="+song]
        return self._calc_rating(matrix, ixs)

    cdef double _calc_rating(self,
            np.ndarray[DOUBLE, ndim=1, mode="c"] matrix, np.ndarray[INTEGER, ndim=1, mode="c"] ixs):
        """
        回帰予測
        """
        cdef:
            # 各特徴量の重み
            double features = 0.0
            # 相互作用の重み
            double iterations = 0.0
            int f
            double dot_sum = 0.0
            double dot_sum_square = 0.0
            long ix
        
        for ix in ixs:
            features += self.W[ix] * matrix[ix]
        for f in xrange(self.K):
            dot_sum = 0.0
            dot_sum_square = 0.0
            for ix in ixs:
                dot_sum += self.V[ix][f] * matrix[ix]
                dot_sum_square += self.V[ix][f] * self.V[ix][f] * matrix[ix] * matrix[ix]
            iterations += dot_sum * dot_sum - dot_sum_square
        return self.w_0 + features + iterations/2

    def save_redis(self, int db = 0):
        """
        パラメータのredisへの保存
        """
        r = redis.Redis(host='localhost', port=6379, db=db)
        
        """
        全て消す
        """
        #r.flushall()
        """
        w_0, W, Vの保存
        """
        # w_0の保存
        print "w_0保存"
        self.save_scalar(r, "bias", "w_0", self.w_0)
        # Wの保存
        print "W保存"
        self.save_one_dim_array(r, "W", self.W)
        # Vの保存
        print "V保存"
        self.save_two_dim_array(r, "V_", self.V)
        """
        regsの保存
        """
        print "regs保存"
        self.save_one_dim_array(r, "regs", self.regs)
        """
        adagradの保存
        """
        # adagrad_w_0の保存
        print "adagrad_w_0保存"
        self.save_scalar(r, "bias", "adagrad", self.adagrad_w_0)
        # adagrad_Wの保存
        print "adagrad_W保存"
        self.save_one_dim_array(r, "adagrad_W", self.adagrad_W)
        # adagrad_Vの保存
        print "adagrad_V保存"
        self.save_two_dim_array(r, "adagrad_V_", self.adagrad_V)

    def save_scalar(self, redis_obj, char* key, char* field, double value):
        redis_obj.hset(key, field, value)

    def save_one_dim_array(self, redis_obj, char* key, np.ndarray[DOUBLE, ndim=1, mode="c"] params):

        cdef:
            double param

        for param in params:
            redis_obj.rpush(key, param)

    def save_two_dim_array(self, redis_obj, char* pre_key, np.ndarray[DOUBLE, ndim=2, mode="c"] params):

        cdef:
            long i
            double param
        
        for i in xrange(self.K):
            key = pre_key + str(i)
            for param in np.transpose(params)[i]:
                redis_obj.rpush(key, param)

    def get_adagrad_W(self):
        return self.adagrad_W

    def get_adagrad_V(self):
        return self.adagrad_V

    def set_W(self, np.ndarray[DOUBLE, ndim=1, mode="c"] W):
        self.W = W

    def set_V(self, np.ndarray[DOUBLE, ndim=2, mode="c"] V):
        self.V = V

    def set_adagrad_W(self, np.ndarray[DOUBLE, ndim=1, mode="c"] adagrad_W):
        self.adagrad_W = adagrad_W

    def set_adagrad_V(self, np.ndarray[DOUBLE, ndim=2, mode="c"] adagrad_V):
        self.adagrad_V = adagrad_V

    def set_n(self, n):
        self.n = n
