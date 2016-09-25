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
    cdef:
        np.ndarray W
        double bias
        
    def __cinit__(self,
            np.ndarray[DOUBLE, ndim=1, mode="c"] W,
            double bias):
        self.W = W
        self.bias = bias

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

    def fit(self):
        return

