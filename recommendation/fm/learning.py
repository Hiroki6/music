# -*- coding:utf-8 -*-

import create_matrix
import redis
import time
import sys
sys.dont_write_bytecode = True 
sys.path.append('./FmSgd')
import fm_lib

"""
学習
db=0に保存
"""
def train():

    start_time = time.time()
    learning_matrix, regs_matrix, labels, targets, tag_map, ratelist = create_matrix.create_fm_matrix()
    print "FMクラス初期化"
    FM_obj = fm_lib.CyFmSgdOpt(learning_matrix, regs_matrix, labels, targets, tag_map)
    print "SGDで学習開始"
    FM_obj.learning(0.005, K=8, step=1)
    FM_obj.arrange_user()
    FM_obj.smoothing()
    print "redisに保存"
    redis_flush()
    FM_obj.cy_fm.save_redis()
    labels = FM_obj.labels
    save_params_into_radis(labels, tag_map) # labelsをredisに保存
    print "top_k_ranking保存"
    FM_obj.save_top_k_ranking_all_user()
    print time.time() - start_time

"""
スムージングの精度評価
db=1に保存
保存するのはスムージング前と後のWとV
"""
def smoothing_validation():

    start_time = time.time()
    learning_matrix, regs_matrix, labels, targets, tag_map, ratelist, train_songs, validation_songs = create_matrix.create_smoothing_fm_matrix()
    redis_flush(db=1)
    save_songs("train_songs", train_songs)
    save_songs("validation_songs", validation_songs)
    print "FMクラス初期化"
    FM_obj = fm_lib.CyFmSgdOpt(learning_matrix, regs_matrix, labels, targets, tag_map)
    print "SGDで学習開始"
    FM_obj.learning(0.005, K=8, step=1)
    FM_obj.arrange_user()
    FM_obj.smoothing(smoothing_evaluate=True)
    print time.time() - start_time

def save_songs(key, songs):

    r = redis.Redis(host='localhost', port=6379, db=1)
    for song in songs:
        r.rpush(key, song)

def save_params_into_radis(labels, tag_map, db=0):
    r = redis.Redis(host='localhost', port=6379, db=db)
    for key, value in labels.items():
        r.rpush("label_keys", key)
        r.rpush("label_values", value)
    
    for key, value in tag_map.items():
        r.hset("tag_map", key, value)

def redis_flush(db=0):

    r = redis.Redis(host='localhost', port=6379, db=db)
    r.flushdb()
