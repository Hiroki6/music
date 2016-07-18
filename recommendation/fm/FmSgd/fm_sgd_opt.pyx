# -*- coding:utf-8 -*-
"""
Factorization Machineをcythonを使って高速化
学習手法は確率的勾配法(SGD)
学習率はAdaGradを使用
正規化項は「Learning Recommender Systems with Adaptive Regularization」参考
"""

from libc.math cimport pow, sqrt
import math
import random
import time
import numpy as np
cimport numpy as np
cimport cython

np.import_array()

ctypedef np.float64_t DOUBLE
ctypedef np.int64_t INTEGER

cdef class CyFmSgdOpt:
    """
    parameters
    R : 学習データ配列(FMフォーマット形式) N * n
    R_v : テスト用データ配列(FMフォーマット形式) regsとgradsの最適化用
    targets : 学習データの教師ラベル N
    w_0 : バイアス 1
    W : 各特徴量の重み n
    V : 各特徴量の相互作用の重み n * K
    E : 各データの予測誤差 N
    adagrad_w_0 : adagradにおけるw_0の保存配列 1
    adagrad_V : adagradにおけるVの保存配列 n * K
    adagrad_W : adagradにおけるWの保存配列 n
    N : 学習データ数
    n : 特徴量の総数
    l_rate : 学習率
    r_param : 勾配率
    K : Vの次元
    step : 学習ステップ数
    regs : regulations 配列 K+2 (0: w_0, 1: W, 2~K+2: V)
    epsilon: 再学習の条件(epsilon - P(f) + P(t))
    top_R: 推薦された楽曲の特徴ベクトル
    feedback_R: フィードバックを考慮した楽曲の特徴ベクトル
    """

    cdef:
        np.ndarray R
        np.ndarray R_v
        np.ndarray targets
        np.ndarray W
        np.ndarray V
        np.ndarray E
        np.ndarray adagrad_V
        np.ndarray adagrad_W
        np.ndarray top_R
        np.ndarray feedback_R
        np.ndarray feature_indexes
        double adagrad_w_0
        double w_0
        long n
        long N
        long N_v
        np.ndarray regs
        double l_rate
        int K
        int step
        double error
        double now_error
        long[:] ixs
        long[:] reg_ixs

    def __cinit__(self,
                    np.ndarray[DOUBLE, ndim=2, mode="c"] R,
                    np.ndarray[DOUBLE, ndim=2, mode="c"] R_v,
                    np.ndarray[INTEGER, ndim=1, mode="c"] targets,
                    np.ndarray[DOUBLE, ndim=1, mode="c"] W,
                    np.ndarray[DOUBLE, ndim=2, mode="c"] V,
                    double w_0,
                    long n,
                    long N,
                    long N_v,
                    np.ndarray[DOUBLE, ndim=1, mode="c"] E,
                    np.ndarray[DOUBLE, ndim=1, mode="c"] regs,
                    double l_rate,
                    int K,
                    int step):
        self.R = R
        self.R_v = R_v
        self.targets = targets
        self.W = W
        self.V = V
        self.w_0 = w_0
        self.n = n
        self.N = N
        self.N_v = N_v
        self.E = E
        self.regs = regs
        self.l_rate = l_rate
        self.K = K
        self.step = step

    def get_sum_error(self):

        cdef:
            long data_index
            int f
            double sum_error = 0.0

        for data_index in xrange(self.N):
            self.ixs = np.nonzero(self.R[data_index])[0]
            sum_error += pow(self._calc_error(data_index), 2)
        
        self.error = sum_error
        self.error += self.regs[0] * pow(self.w_0, 2) + self.regs[1] * np.sum(self.W**2)
        for f in xrange(self.K):
            self.error += self.regs[f+2] * np.sum(np.transpose(self.V)[f]**2)

        
    def get_all_error(self):
        """
        全ての学習データの誤差を計算
        """
        cdef:
            long data_index

        for data_index in xrange(self.N):
            print data_index
            self._get_error(data_index)

    cdef void _get_error(self, long data_index):
        """
        誤差計算
        """
        cdef:
            double features = 0.0
            double iterations = 0.0
            int f
    
        features = np.dot(self.W, self.R[data_index])
        for f in xrange(self.K):
            iterations += pow(np.dot(self.V[:,f], self.R[data_index]), 2) - np.dot(self.V[:,f]*self.V[:,f], self.R[data_index]*self.R[data_index])

        self.E[data_index] = (self.w_0 + features + iterations/2) - self.targets[data_index]

    cdef void _update_w_0(self, long data_index):
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

    cdef void _update_W(self, long data_index, long i):
        """
        W[i]の更新
        """
        cdef:
            double grad_value = 0.0
            double update_value = 0.0

        grad_value = 2 * (self.now_error*self.R[data_index][i] + self.regs[1]*self.W[i])
        self.adagrad_W[i] += grad_value * grad_value
        update_value = self.l_rate * grad_value / sqrt(self.adagrad_W[i])
        self.W[i] -= update_value

    cdef void _update_V(self, long data_index, long i, int f):
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
            h_pre += self.V[ix][f] * self.R[data_index][f]
        h = h_pre - self.V[i][f]*self.R[data_index][i]
        h *= self.R[data_index][i]
        grad_value = 2 * (self.now_error*h + self.regs[f+2]*self.V[i][f])
        self.adagrad_V[i][f] += grad_value * grad_value
        update_value = self.l_rate * grad_value / sqrt(self.adagrad_V[i][f])
        self.V[i][f] -= update_value

    def repeat_optimization(self):
 
        cdef:
            long ix
            int f
            long data_index
            double pre_w_0
            double s
            np.ndarray[DOUBLE, ndim=1, mode="c"] pre_W
            np.ndarray[DOUBLE, ndim=2, mode="c"] pre_V

        for data_index in xrange(self.N):
            """
            パラメータの最適化
            """
            # 前回の正規化パラメータ
            pre_w_0 = self.w_0
            pre_W = self.W
            pre_V = self.V
            print "data_index %d" % data_index
            self.ixs = np.nonzero(self.R[data_index])[0]
            self.now_error = self._calc_error(data_index)
            self._update_w_0(data_index)
            for ix in self.ixs:
                self._update_W(data_index, ix)
                for f in xrange(self.K):
                    self._update_V(data_index, ix, f)
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
        
        random_index = random.randint(0, self.N_v-1)
        self.reg_ixs = np.nonzero(self.R_v[random_index])[0]
        err = 2 * self._calc_error(random_index)
        # lambda_0
        new_r = self.regs[0] - self.l_rate * (err * -2 * self.l_rate * pre_w_0)
        self.regs[0] = new_r if new_r >= 0 else 0
        # lambda_w
        new_r = self.regs[1] - self.l_rate * (err * -2 * self.l_rate * np.dot(pre_W, self.R_v[random_index]))
        self.regs[1] = new_r if new_r >= 0 else 0
        for f in xrange(self.K):
            # lambda_v_f
            dot_r_v = 0.0
            dot_r_v_pre = 0.0
            dot_sum = 0.0
            for ix in self.reg_ixs:
                dot_r_v += self.R_v[random_index][ix] * self.V[ix][f]
                dot_r_v_pre += self.R_v[random_index][ix] * pre_V[ix][f]
                dot_sum += self.R_v[random_index][ix] * self.R_v[random_index][ix] * self.V[ix][f] * pre_V[ix][f]
            new_r = self.regs[f+2] - self.l_rate * (err * -2 * self.l_rate * dot_r_v * dot_r_v_pre - dot_sum)
            self.regs[f+2] = new_r if new_r >= 0 else 0

    cdef double _calc_error(self, long data_index):
        """
        ２乗誤差の計算
        """
        cdef:
            double features = 0.0
            double iterations = 0.0
            int f
            double dot_sum = 0.0
            double dot_square_sum = 0.0
            long ix
            double start_time

        for ix in self.ixs:
            features += self.W[ix] * self.R[data_index][ix]
            # 間違えている可能性がある
        for f in xrange(self.K):
            dot_sum = 0.0
            dot_square_sum = 0.0
            for ix in self.ixs:
                dot_sum += self.V[ix][f] * self.R[data_index][ix]
                dot_square_sum += self.V[ix][f] * self.V[ix][f] * self.R[data_index][ix] * self.R[data_index][ix]
            iterations += dot_sum * dot_sum - dot_square_sum

        return (self.w_0 + features + iterations/2) - 1.0
    
    cdef double _calc_error_regs(self, long data_index):
        """
        ２乗誤差の計算(正規化項用)
        """
        cdef:
            double features = 0.0
            double iterations = 0.0
            int f
            double dot_sum = 0.0
            double dot_square_sum = 0.0
            long ix
            double start_time

        for ix in self.reg_ixs:
            features += self.W[ix] * self.R_v[data_index][ix]
            # 間違えている可能性がある
        for f in xrange(self.K):
            dot_sum = 0.0
            dot_square_sum = 0.0
            for ix in self.reg_ixs:
                dot_sum += self.V[ix][f] * self.R_v[data_index][ix]
                dot_square_sum += self.V[ix][f] * self.V[ix][f] * self.R_v[data_index][ix] * self.R_v[data_index][ix]
            iterations += dot_sum * dot_sum - dot_square_sum

        return (self.w_0 + features + iterations/2) - 1.0

    def learning(self):
        """
        初期の学習
        """
        cdef:
            int s

        self.adagrad_w_0 = 0.0
        self.adagrad_W = np.zeros(self.n)
        self.adagrad_V = np.zeros((self.n, self.K))
        for s in xrange(self.step):
            print "Step %d" % s
            self.repeat_optimization()
            self.get_sum_error()
            if self.error <= 100:
                break

    cdef double _calc_rating(self,
                    np.ndarray[DOUBLE, ndim=1, mode="c"] matrix):
        """
        回帰予測
        """
        cdef:
            # 各特徴量の重み
            double features = 0.0
            # 相互作用の重み
            double iterations = 0.0
            int f

        features = np.dot(self.W, matrix)
        for f in xrange(self.K):
            iterations += pow(np.dot(self.V[:,f], matrix), 2) - np.dot(self.V[:,f]**2, matrix**2)
        return self.w_0 + features + iterations/2

    def predict(self, np.ndarray[DOUBLE, ndim=1, mode="c"] matrix):
        """
        python側から呼び出せる回帰予測結果取得
        """
        return self._calc_rating(matrix)

    def get_w_0(self):
        return self.w_0

    def get_W(self):
        return self.W

    def get_V(self):
        return self.V

    def get_E(self):
        return self.E

    def get_self_error(self):
        return self.error

    def get_epsilon(self):
        return self.epsilon

    def get_adagrad_w_0(self):
        return self.adagrad_w_0

    def get_adagrad_W(self):
        return self.adagrad_W

    def get_adagrad_V(self):
        return self.adagrad_V
