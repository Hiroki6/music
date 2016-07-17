# -*- coding:utf-8 -*-

import numpy as np
import math
import fm_sgd_opt
import redis
import sys
sys.dont_write_bytecode = True 

class CyFmSgdOpt():
    """
    parameters
    R : 学習データ配列(FMフォーマット形式) N * n
    R_v : テスト用データ配列(FMフォーマット形式) regsとgradsの最適化用
    targets : 学習データの教師ラベル N
    seed : シード(V用)
    init_stde : 分散(V用)
    w_0 : バイアス 1
    W : 各特徴量の重み n
    V : 各特徴量の相互作用の重み n * K
    E : 各データの予測誤差 N
    N : 学習データ数
    n : 特徴量の総数
    K : Vの次元
    regs : regulations 配列 K+2 (0: w_0, 1: W, 2~K+2: V)
    """

    def __init__(self, R, R_v, labels, targets, seed=20, init_stdev=0.01):
        self.R = R #評価値行列
        self.labels = labels
        self.targets = targets # 教師配列
        self.R_v = R_v
        self.n = len(self.R[0])
        self.N_v = len(self.R_v)
        self.N = len(self.R)
        self.E = np.zeros(self.N)
        self.seed = seed
        self.init_stdev = init_stdev

    def learning(self, l_rate, K=16, step=30):

        self.w_0 = 0.0
        self.W = np.zeros(self.n)
        np.random.seed(seed=self.seed)
        self.V = np.random.normal(scale=self.init_stdev,size=(self.n, K))
        self.regs = np.zeros(K+2)
        self.K = K
        # cythonクラスインスタンス初期化
        self.cython_FM = fm_sgd_opt.CyFmSgdOpt(self.R, self.R_v, self.targets, self.W, self.V, self.w_0, self.n, self.N, self.N_v, self.E, self.regs, l_rate, K, step)
        # 学習
        self.cython_FM.learning()

    def save_redis(self):
        """
        パラメータのredisへの保存
        """
        r = redis.Redis(host='localhost', port=6379, db=0)
        
        """
        全て消す
        """
        r.flushall()
        """
        w_0, W, Vの保存
        """
        w_0 = self.cython_FM.get_w_0()
        # w_0の保存
        self.save_scalar(r, "bias", "w_0", w_0)
        # Wの保存
        self.save_one_dim_array(r, "W", self.W)
        # Vの保存
        self.save_two_dim_array(r, "V_", self.V)
        """
        regsの保存
        """
        self.save_one_dim_array(r, "regs", self.regs)
        """
        adagradの保存
        """
        adagrad_w_0 = self.cython_FM.get_adagrad_w_0()
        adagrad_W = self.cython_FM.get_adagrad_W()
        adagrad_V = self.cython_FM.get_adagrad_V()
        # adagrad_w_0の保存
        self.save_scalar(r, "bias", "adagrad", adagrad_w_0)
        # adagrad_Wの保存
        self.save_one_dim_array(r, "adagrad_W", adagrad_W)
        # adagrad_Vの保存
        self.save_two_dim_array(r, "adagrad_V_", adagrad_V)

    def save_scalar(self, redis_obj, key, field, value):
        redis_obj.hset(key, field, value)

    def save_one_dim_array(self, redis_obj, key, params):
        for param in params:
            redis_obj.rpush(key, param)

    def save_two_dim_array(self, redis_obj, pre_key, params):
        for i in xrange(len(params)):
            key = pre_key + str(i)
            for param in params[i]:
                redis_obj.rpush(key, param)
