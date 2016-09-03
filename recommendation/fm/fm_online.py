# -*- coding:utf-8 -*-

import numpy as np
import math
import create_matrix
from FmOnline import cy_fm_online
import redis
from .. import models
import time
import codecs
import random
import sys
sys.dont_write_bytecode = True 
import os.path
BASE = os.path.dirname(os.path.abspath(__file__))
HOST = 'localhost'
PORT = 6379

class FmOnline:
    """
    seed : シード(V用)
    init_stde : 分散(V用)
    w_0 : バイアス 1
    W : 各特徴量の重み n
    V : 各特徴量の相互作用の重み n * K
    n : 特徴量の総数
    labels: {feature: index}
    rate_dic: 学習用データ{artist: [songs]}
    """

    def __init__(self, labels, tag_map, seed=20, init_stdev=0.01):
        self.labels = labels
        self.tag_map = tag_map
        self.n = len(labels)
        self.seed = seed
        self.init_stdev = init_stdev

    def prepare_train(self, l_rate, K=16, step=30):
        """
        モデルパラメータとcy_fm_onlineクラスのセットアップ
        """
        self.w_0 = 0.0
        self.W = np.zeros(self.n)
        np.random.seed(seed=self.seed)
        self.V = np.random.normal(scale=self.init_stdev,size=(self.n, K))
        self.regs = np.zeros(K+2)
        self.K = K
        # cythonクラスインスタンス初期化
        self.cy_fm = cy_fm_online.CyFmOnline(self.W, self.V, self.w_0, self.n, self.regs, l_rate, K, step, self.labels)
        self.rate_dic, self.rate_nums, self.regs_dic, self.regs_num = create_matrix.get_ratelist()
        self.song_tags = create_matrix.get_song_tags()

    def fit(self, step=1):
        """
        ratelistから逐次的にcy_fmに渡して学習を行う
        """
        for i in xrange(step):
            data_index = 0
            for user, songs in self.rate_dic.items():
                user_index = self.labels["user="+user]
                for index, song in enumerate(songs):
                    create_flag = True
                    train_data, create_flag = self.create_fm_matrix(user_index, song)
                    regs_data, create_flag = self.create_regs_data()
                    if create_flag:
                        print "data_index %d" % (data_index)
                        self.cy_fm.fit(train_data, regs_data)
                        data_index += 1

    def create_fm_matrix(self, user_index, song):

        fm_data = np.zeros(self.n)
        song_label_name = "song=" + song
        create_flag = True
        if self.labels.has_key(song_label_name):
            song_index = self.labels[song_label_name]
            fm_data[user_index] = 1.0
            fm_data[song_index] = 1.0
            for tag_index, tag_value in enumerate(self.song_tags[song]):
                fm_data[self.tag_map[tag_index]] = tag_value
        else:
            create_flag = False

        return fm_data, create_flag
    
    def create_regs_data(self):
        
        user = random.choice(self.regs_dic.keys())
        user_index = self.labels["user="+user]
        song_index = random.randint(0, len(self.regs_dic[user])-1)
        song = self.regs_dic[user][song_index]
        return self.create_fm_matrix(user_index, song)

    def calc_error(self):
    
        error = 0.0
        data_index = 0
        for user, songs in self.rate_dic.items():
            user_index = self.labels["user="+user]
            for index, song in enumerate(songs):
                train_data, create_flag = self.create_fm_matrix(user_index, song)
                if create_flag:
                    print "data_index %d" % (data_index)
                    error += pow(self.cy_fm.calc_error(train_data), 2)
                    data_index += 1
        error += self.cy_fm.calc_all_regs()
        print error
