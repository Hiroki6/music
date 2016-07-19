# -*- coding:utf-8 -*-

import numpy as np
cimport numpy as np
cimport cython
import sys
from libc.math cimport pow, sqrt

np.import_array()

ctypedef np.float64_t DOUBLE
ctypedef np.int64_t INTEGER

cdef class CyRecommendFm:
    """
    parameters
    w_0 : バイアス 1
    W : 各特徴量の重み n
    V : 各特徴量の相互作用の重み n * K
    E : 各データの予測誤差 N
    adagrad_w_0 : adagradにおけるw_0の保存配列 1
    adagrad_V : adagradにおけるVの保存配列 n * K
    adagrad_W : adagradにおけるWの保存配列 n
    n : 特徴量の総数
    l_rate : 学習率
    K : Vの次元
    step : 学習ステップ数
    regs : regulations 配列 K+2 (0: w_0, 1: W, 2~K+2: V)
    epsilon: 再学習の条件(epsilon - P(f) + P(t))
    top_R: 推薦された楽曲の特徴ベクトル
    feedback_R: フィードバックを考慮した楽曲の特徴ベクトル
    ixs: 0でない要素のインデックス
    """

    cdef:
        np.ndarray W
        np.ndarray V
        np.ndarray E
        np.ndarray adagrad_W
        np.ndarray adagrad_V
        np.ndarray top_R
        np.ndarray feedback_R
        np.ndarray regs
        double adagrad_w_0
        double w_0
        long n
        int K
        double epsilon
        double l_rate
        long[:] ixs
        dict labels
    
    def __cinit__(self,
                    double w_0,
                    np.ndarray[DOUBLE, ndim=1, mode="c"] W,
                    np.ndarray[DOUBLE, ndim=2, mode="c"] V,
                    double adagrad_w_0,
                    np.ndarray[DOUBLE, ndim=1, mode="c"] adagrad_W,
                    np.ndarray[DOUBLE, ndim=2, mode="c"] adagrad_V,
                    np.ndarray[DOUBLE, ndim=1, mode="c"] regs,
                    long n,
                    int K,
                    double l_rate,
                    dict labels):
        self.w_0 = w_0
        self.W = W
        self.V = V
        self.adagrad_W = adagrad_W
        self.adagrad_V = adagrad_V
        self.adagrad_w_0 = adagrad_w_0
        self.regs = regs
        self.n = n
        self.K = K
        self.l_rate = l_rate
        self.labels = labels

    cdef double _calc_rating(self,
            np.ndarray[DOUBLE, ndim=1, mode="c"] matrix, char* song, np.ndarray[INTEGER, ndim=1, mode="c"] ixs):
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
        
        ixs[-1] = self.labels["song="+song]
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

    def predict(self, np.ndarray[DOUBLE, ndim=1, mode="c"] matrix, char* song, np.ndarray[INTEGER, ndim=1, mode="c"] ixs):
        """
        python側から呼び出せる回帰予測結果取得
        """
        return self._calc_rating(matrix, song, ixs)

    def get_top_song(self, np.ndarray[DOUBLE, ndim=2, mode="c"] matrixes, np.ndarray[INTEGER, ndim=1, mode="c"] songs):

        cdef:
            double top_value = -sys.maxint
            np.ndarray top_matrix = matrixes[0]
            int top_song = songs[0]
            np.ndarray matrix
            int song
            double predict_value

        for matrix, song in zip(matrixes, songs):
            predict_value = self.predict(matrix)
            if top_value < predict_value:
                top_value = predict_value
                top_matrix = matrix
                top_song = song

        return top_song

    def relearning(self, np.ndarray[DOUBLE, ndim=1, mode="c"] top_matrix, np.ndarray[DOUBLE, ndim=1, mode="c"] feedback_matrix):
        """
        フィードバックによる再学習
        top_matrix: 推薦された楽曲の特徴ベクトル
        feedback_matrix: フィードバックを考慮した楽曲の特徴ベクトル
        """
        cdef:
            double top_predict
            double feedback_predict
            int count

        self.feedback_R = feedback_matrix
        self.top_R = top_matrix
        self.ixs = np.nonzero(top_matrix)[0]
        self._decition_epsilon(top_matrix, feedback_matrix)  # epsilonの決定
        top_predict, feedback_predict, feedback_error = self.calc_feedback_error(top_matrix, feedback_matrix)
        print feedback_error
        count = 0
        while feedback_error > 0.0:
            print count
            self.relearning_optimization(top_predict, feedback_predict)
            top_predict, feedback_predict, feedback_error = self.calc_feedback_error(top_matrix, feedback_matrix)
            print feedback_error
            count += 1
            if(count > 1000):
                break

    def relearning_optimization(self, double top_predict, double feedback_predict):
        """
        再学習による最適化
        """
        cdef:
            long ix
            int f
            long index
    
        for ix in self.ixs:
            #self._reupdate_W(ix)
            for f in xrange(self.K):
                self._reupdate_V(ix, f)

    def calc_feedback_error(self, np.ndarray[DOUBLE, ndim=1, mode="c"] top_matrix, np.ndarray[DOUBLE, ndim=1, mode="c"] feedback_matrix):
        """
        誤差の計算{ε-y(X_f)+y(X_t)}
        @returns(top_predict) 推薦曲の予測値
        @returns(feed_predict) フィードバックを考慮したもの予測値
        """
        top_predict = self.predict(top_matrix)
        feedback_predict = self.predict(feedback_matrix)
        feedback_error = self.epsilon - feedback_predict + top_predict

        return top_predict, feedback_predict, feedback_error

    cdef void _decition_epsilon(self, np.ndarray[DOUBLE, ndim=1, mode="c"] top_matrix, np.ndarray[DOUBLE, ndim=1, mode="c"] feedback_matrix):
        """
        εの決定
        """
        top_predict = self.predict(top_matrix)
        feedback_predict = self.predict(feedback_matrix)
        # もともと値が大きい時
        if feedback_predict > top_predict:
            self.epsilon = 2 * (feedback_predict - top_predict)
        # 値が小さい時
        else:
            self.epsilon = - (feedback_predict - top_predict)
    
    def set_epsilon(self, epsilon):
        """
        python側からのεの設定
        """
        self.epsilon = epsilon

    cdef void _reupdate_W(self, long i):
        """
        W[i]の再更新
        """
        cdef:
            double grad_value = 0.0
            double update_value = 0.0
    
        grad_value = -self.feedback_R[i] + self.top_R[i] + 2*self.regs[1]*self.W[i]
        self.adagrad_W[i] += grad_value * grad_value
        update_value = self.l_rate * grad_value / sqrt(self.adagrad_W[i])
        self.W[i] -= update_value

    cdef void _reupdate_V(self, long i, int f):
        """
        V[i][f]の再更新
        """
        cdef:
            double grad_value = 0.0
            double update_value = 0.0
            double h_f_pre = 0.0
            double h_t_pre = 0.0
            double h_f = 0.0 # feedback部分
            double h_t = 0.0 # top部分
            
        for ix in self.ixs:
            h_f_pre += self.V[ix][f] * self.feedback_R[ix]
            h_t_pre += self.V[ix][f] * self.top_R[ix]
        h_f = h_f_pre - self.V[i][f] * self.feedback_R[i]
        h_f *= self.feedback_R[i]
        h_t = h_t_pre - self.V[i][f] * self.top_R[i]
        h_t *= self.top_R[i]
        grad_value = -h_f + h_t + 2*self.regs[f+2]*self.V[i][f]
        self.adagrad_V[i][f] += grad_value * grad_value
        update_value = self.l_rate * grad_value / sqrt(self.adagrad_V[i][f])
        self.V[i][f] -= update_value
