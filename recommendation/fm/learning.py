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
"""
def learning():

    start_time = time.time()
    learning_matrix, regs_matrix, labels, targets, tag_map, ratelist = create_matrix.create_fm_matrix()
    print "FMクラス初期化"
    FM_obj = fm_lib.CyFmSgdOpt(learning_matrix, regs_matrix, labels, targets, tag_map)
    print "SGDで学習開始"
    FM_obj.learning(0.005, K=8, step=1)
    FM_obj.arrange_user()
    FM_obj.smoothing()
    print "redisに保存"
    FM_obj.cy_fm.save_redis()
    labels = FM_obj.labels
    save_params_into_radis(labels, tag_map) # labelsをredisに保存
    print "top_k_ranking保存"
    FM_obj.save_top_k_ranking_all_user()
    print time.time() - start_time

"""
スムージングの精度評価
"""
def smoothing_learning():

    start_time = time.time()
    learning_matrix, regs_matrix, labels, targets, tag_map, ratelist, train_songs, validation_songs = create_matrix.create_smoothing_fm_matrix()
    print "FMクラス初期化"
    FM_obj = fm_lib.CyFmSgdOpt(learning_matrix, regs_matrix, labels, targets, tag_map)
    print "SGDで学習開始"
    FM_obj.learning(0.005, K=8, step=1)
    FM_obj.arrange_user()
    FM_obj.smoothing()
    print "redisに保存"
    FM_obj.cy_fm.save_redis(1)
    labels = FM_obj.labels
    save_params_into_radis(labels, tag_map) # labelsをredisに保存
    print time.time() - start_time

def save_params_into_radis(labels, tag_map):
    r = redis.Redis(host='localhost', port=6379, db=0)
    for key, value in labels.items():
        r.rpush("label_keys", key)
        r.rpush("label_values", value)
    
    for key, value in tag_map.items():
        r.hset("tag_map", key, value)
