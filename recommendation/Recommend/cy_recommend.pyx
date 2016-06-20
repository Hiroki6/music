# -*- coding:utf-8 -*-

import numpy as np
cimport numpy as np
cimport cython
import sys

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
    """

    cdef:
        np.ndarray W
        np.ndarray V
        np.ndarray E
        np.ndarray adagrad_W
        np.ndarray adagrad_V
        np.ndarray top_R
        np.ndarray feedback_R
        np.ndarray feature_indexes
        np.ndarray regs
        double adagrad_w_0
        double w_0
        long n
        int K
    
    def __cinit__(self,
                    double w_0,
                    np.ndarray[DOUBLE, ndim=1, mode="c"] W,
                    np.ndarray[DOUBLE, ndim=2, mode="c"] V,
                    double adagrad_w_0,
                    np.ndarray[DOUBLE, ndim=1, mode="c"] adagrad_W,
                    np.ndarray[DOUBLE, ndim=2, mode="c"] adagrad_V,
                    np.ndarray[DOUBLE, ndim=1, mode="c"] regs,
                    long n,
                    int K):
        self.w_0 = w_0
        self.W = W
        self.V = V
        self.adagrad_W = adagrad_W
        self.adagrad_V = adagrad_V
        self.adagrad_w_0 = adagrad_w_0
        self.regs = regs
        self.n = n
        self.K = K

    cdef double _calc_rating(self, np.ndarray[DOUBLE, ndim=1, mode="c"] matrix):
        """
        回帰予測
        """
        cdef:
            double features = 0.0
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
