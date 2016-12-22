# -*- coding:utf-8 -*-
from libc.math cimport pow, sqrt
import numpy as np
cimport numpy as np
cimport cython

np.import_array()

ctypedef np.float64_t DOUBLE
ctypedef np.int64_t INTEGER

def get_euclid_distance(np.ndarray[DOUBLE, ndim=1] vector1, np.ndarray[DOUBLE, ndim=1] vector2, long degree):

    cdef:
        double euclid_distance = 0.0
        double sum_distance = 0.0
        long index

    for index in xrange(degree):
        sum_distance += pow(vector1[index] - vector2[index], 2)

    distance = sqrt(sum_distance)
    return distance
