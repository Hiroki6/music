# -*- coding:utf-8 -*-

import create_matrix
import redis
import time
import sys
sys.dont_write_bytecode = True 
import smoothing_lib
sys.path.append('./FmSgd')
import fm_lib
import fm_online

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
    #FM_obj.smoothing()
    print "redisに保存"
    redis_flush()
    FM_obj.cy_fm.save_redis()
    labels = FM_obj.labels
    save_params_into_radis(labels, tag_map) # labelsをredisに保存
    #print "top_k_ranking保存"
    #FM_obj.save_top_k_ranking_all_user()
    smoothing()
    print "top_k_ranking保存"
    FM_obj.save_top_k_ranking_all_user(smoothing_flag = True)
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
    FM_obj.cy_fm.save_redis(db=1)
    labels = FM_obj.labels
    save_params_into_radis(labels, tag_map) # labelsをredisに保存

    #FM_obj.smoothing(smoothing_evaluate=True)
    smoothing(smoothing_evaluate=True)
    print time.time() - start_time

def smoothing(smoothing_evaluate=False):

    s_obj = smoothing_lib.SmoothingFm(8, smoothing_evaluate)
    s_obj.learning()
    s_obj.smoothing()

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

"""
FMのオンライン学習
逐次的にデータを読み込む(メモリ削減のため)
"""
def online_train():

    data_labels, tag_map = create_matrix.get_data_labels_and_tag_map()

    fm_obj = fm_online.FmOnline(data_labels, tag_map)
    fm_obj.prepare_train(0.005, K=8, step=1)
    fm_obj.fit(5)
    fm_obj.calc_error()
