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

cdef class CyEmotionFeedback:
    """
    W: 重み行列
    margin: ヒンジ損失のマージン
    """
    cdef:
        np.ndarray W
        double margin
        double error

    def __cinit__(self,
            np.ndarray[DOUBLE, ndim=1, mode="c"] W):
        self.W = W

    def predict(self, np.ndarray[DOUBLE, ndim=1, mode="c"] X):
        """
        特徴ベクトルXに対する回帰予測
        """
        return np.dot(self.W, X)

    def calc_error(self, np.ndarray[DOUBLE, ndim=1, mode="c"] X):
        """
        回帰誤差計算
        """
        return self.margin - self.predict(X)

    def set_margin(self, np.ndarray[DOUBLE, ndim=1, mode="c"] X):
        """
        X: フィードバック要素を含んだものとフィードバックされた楽曲の特徴ベクトルの差ベクトル(X_f - X_t)
        初期予測値が>0の時は2*predict_valueをマージンにして、<0のときは0まで学習する
        """
        cdef:
            double predict_value

        predict_value = self.predict(X)
        if predict_value > 0:
            self.margin = 2 * self.predict(X)
        else:
            self.margin = -1 * self.predict(X)
        print self.margin
        
    def fit(self, np.ndarray[DOUBLE, ndim=1, mode="c"] X, bint normal = False):
    
        if normal:
            self.margin = 0.0
        else:
            self.set_margin(X)
        self._repeat_optimization(X)

    def _repeat_optimization(self, np.ndarray[DOUBLE, ndim=1, mode="c"] X):
        
        cdef:
            int i
        self.error = self.calc_error(X)
        for i in xrange(1000):
            if self.error <= 0:
                print i
                break
            else:
                self._update_W(X)
            self.error = self.calc_error(X)

    def _update_W(self, np.ndarray[DOUBLE, ndim=1, mode="c"] X):
        
        cdef:
            double tau

        tau = self.error / np.linalg.norm(X)
        self.W += tau * X
