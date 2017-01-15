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
        double C
        double lmd

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
        cdef:
            double predict_value
        predict_value = self.predict(X)
        return self.margin - predict_value

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

    def PARank_fit(self, dict bound_song_tag_map, np.ndarray[DOUBLE, ndim=1, mode="c"] top_matrix, double C):
        """
        Passive-Aggressive Perceptronアルゴリズムを用いた学習
        """
        cdef:
            long song
            np.ndarray tags
            np.ndarray X
            int i
            double all_error = 0.0
            long count
            np.ndarray w
   
        self.margin = 0.0
        self.C = C
        w = np.zeros(44)
        count = 0
        for i in xrange(1000):
            all_error = 0.0
            for song, tags in bound_song_tag_map.items():
                X = tags - top_matrix
                self.error = self.calc_error(X)
                if self.error <= 0:
                    continue
                self._update_W_by_PARank(X)
                w += self.W
                count += 1
                all_error += self.error
            if all_error <= 0:
                break
        if count > 0:
            self.W = w / count
        print self.W
        return self.W

    def _repeat_optimization(self, np.ndarray[DOUBLE, ndim=1, mode="c"] X):
        
        cdef:
            int i
        self.error = self.calc_error(X)
        for i in xrange(1000):
            if self.error <= 0:
                if i > 0:
                    print i
                break
            else:
                self._update_W_by_PARank(X)
            self.error = self.calc_error(X)

    def pagasos_fit(self, dict bound_song_tag_map, np.ndarray[DOUBLE, ndim=1, mode="c"] top_matrix, double lmd):
        """
        pagasosを用いた学習
        """
        cdef:
            long song
            np.ndarray tags
            np.ndarray X
            int i
            double all_error = 0.0
            int count
   
        self.lmd = lmd
        count = 0
        for i in xrange(1, 1001):
            all_error = 0.0
            for song, tags in bound_song_tag_map.items():
                X = tags - top_matrix
                self.error = self.calc_error(X)
                if self.error <= 0:
                    self._update_W_by_pagasos(X, i, False)
                    continue
                self._update_W_by_pagasos(X, i, True)
                count += 1
                all_error += self.error
            if all_error <= 0:
                print count
                break
        return self.W

    def _update_W_by_PARank(self, np.ndarray[DOUBLE, ndim=1, mode="c"] X):
        """
        Passive-Aggressive Perceptronアルゴリズムを用いた更新
        """
        cdef:
            double tau

        tau = self.error / np.linalg.norm(X) # PA-I
        #tau = self.error / (np.linalg.norm(X)+1/(2*self.C)) # PA-II
        #print "tau: %.8f" % (tau)
        self.W += min(self.C, tau) * X
        #self.W += tau * X

    def _update_W_by_pagasos(self, np.ndarray[DOUBLE, ndim=1, mode="c"] X, int iteration, bint is_update):
        """
        pagasosを用いた更新
        """
        cdef:
            double eta
            double new_param

        eta = 1 / (self.lmd * iteration)
        self.W *= (1 - 1/iteration)
        if is_update:
            self.W += eta * self.error * X
        new_param = (1/math.sqrt(self.lmd))/np.linalg.norm(self.W)
        self.W = min(1, new_param) * self.W
