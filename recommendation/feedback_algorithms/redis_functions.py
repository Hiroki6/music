# -*- coding:utf-8 -*-

import redis
import numpy as np

def get_scalar(redis_obj, key, field):
    """
    redisからのスカラー値の取得
    """
    return float(redis_obj.hget(key, field))

def get_one_dim_params(redis_obj, key):
    """
    redisから一次元配列の取得
    np.float64
    """
    params = redis_obj.lrange(key, 0, -1)
    params = np.array(params, dtype=np.float64)
    return params

def get_two_dim_by_redis(redis_obj, pre_key, n, m):
    """
    redisから二次元配列の取得
    np.float64
    """
    V = np.ones((m, n))
    for i in xrange(m):
        key = pre_key + str(i)
        v = redis_obj.lrange(key, 0, -1)
        V[i] = v
    V = np.array(V, dtype=np.float64)
    return V.T.copy(order='C')

def get_init_songs_by_redis(key):
    """
    redisから初期検索の楽曲配列を取得
    """
    redis_obj = get_redis_obj('localhost', 6379, 1)
    params = redis_obj.lrange(key, 0, -1)
    params = np.array(params, dtype=np.int64)
    return params

def save_scalar(redis_obj, key, field, value):
    """
    スカラー値の保存
    """
    redis_obj.hset(key, field, value)

def save_one_dim_array(redis_obj, key, params):
    """
    redisへの一次元配列の保存
    """
    for param in params:
        redis_obj.rpush(key, param)

def save_two_dim_array(redis_obj, pre_key, params):
    """
    redisへの二次元配列の保存
    """
    for i in xrange(len(params)):
        key = pre_key + str(i)
        for param in params[i]:
            redis_obj.rpush(key, param)

def get_one_dim_params_int(redis_obj, key):
    """
    redisから一次元配列の取得
    np.float64
    """
    params = redis_obj.lrange(key, 0, -1)
    params = np.array(params, dtype=np.int64)
    return params

def get_redis_obj(host, port, db):
    return redis.Redis(host=host, port=port, db=db)

def get_next_elem_by_pop(redis_obj, key, listening_count):
    """
    まず前の分をpopして捨てる
    """
    return redis_obj.lindex(key, listening_count)

def delete_redis_keys(redis_obj, keys):
    for key in keys:
        delete_redis_key(redis_obj, key)

def delete_redis_key(redis_obj, key):
    redis_obj.delete(key)

def update_redis_key(redis_obj, key, params):
    delete_redis_key(redis_obj, key)
    save_one_dim_array(redis_obj, key, params)

