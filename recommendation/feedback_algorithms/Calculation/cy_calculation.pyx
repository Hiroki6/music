# -*- coding:utf-8 -*-
from libc.math cimport pow, sqrt
import numpy as np
cimport numpy as np
cimport cython

np.import_array()

ctypedef np.float64_t DOUBLE
ctypedef np.int64_t INTEGER

def euclid_distance(np.ndarray[DOUBLE, ndim=1] vector1, np.ndarray[DOUBLE, ndim=1] vector2, long degree):

    cdef:
        double euclid_distance = 0.0
        double sum_distance = 0.0
        long index

    for index in xrange(degree):
        sum_distance += pow(vector1[index] - vector2[index], 2)

    distance = sqrt(sum_distance)
    return distance

def euclid_distance_for_dict(dict map1, dict map2, int degree, char** tags):

    cdef:
        double euclid_distance = 0.0
        double sum_distance = 0.0
        int index

    for index in xrange(degree):
        sum_distance += pow(map1[tags[index]] - map2[tags[index]], 2)

    distance = sqrt(sum_distance)
    return distance

