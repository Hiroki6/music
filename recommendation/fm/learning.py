# -*- coding:utf-8 -*-

import create_matrix
import redis
import sys
sys.dont_write_bytecode = True 
sys.path.append('./FmSgd')
import fm_lib

"""
学習データの読み込み
"""
def learning():

    learning_matrix, regs_matrix, labels, targets, tag_map, ratelist = create_matrix.create_matrix_with_tag_dicVec()
    print "FMクラス初期化"
    FM_obj = fm_lib.CyFmSgdOpt(learning_matrix, regs_matrix, labels, targets, tag_map)
    print "SGDで学習開始"
    FM_obj.learning(0.005, K=8, step=1)
    print "redisに保存"
    FM_obj.cy_fm.save_redis()
    save_params_into_radis(labels, tag_map) # labelsをredisに保存
    print "top_k_ranking保存"
    FM_obj.save_top_k_ranking_all_user()

def save_params_into_radis(labels, tag_map):
    r = redis.Redis(host='localhost', port=6379, db=0)
    for key, value in labels.items():
        r.rpush("label_keys", key)
        r.rpush("label_values", value)
    
    for key, value in tag_map.items():
        r.hset("tag_map", key, value)
