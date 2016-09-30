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
