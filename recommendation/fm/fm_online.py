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
    seed: 乱数しーど
    init_stdev: 正規分布の合計値
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
        """
        fm配列に変換
        """
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
        """
        regs用のデータをランダムに一つ抽出
        """
        user = random.choice(self.regs_dic.keys())
        user_index = self.labels["user="+user]
        song_index = random.randint(0, len(self.regs_dic[user])-1)
        song = self.regs_dic[user][song_index]
        return self.create_fm_matrix(user_index, song)

    def calc_error(self):
        """
        損失関数計算
        """
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

    """
    各ユーザーの楽曲のランキングの取得
    """
    def save_top_k_ranking_all_user(self, smoothing_flag = False):
        """
        アプリのユーザーの未視聴のうちのtop10曲を予測し、redisに保存する
        """
        # スムージングをした場合は、WとVを再読み込み
        if smoothing_flag:
            print "新しいパラメータ取得"
            self.set_W_and_V()
            self.cy_fm.set_W(self.W)
            self.cy_fm.set_V(self.V)

        uniq_users = models.Preference.objects.all().values_list("user", flat=True).order_by("user").distinct()
        if len(uniq_users) == 0:
            return
        for user in uniq_users:
            self.user = user
            self.save_top_k_ranking_one_user()

    def save_top_k_ranking_one_user(self):
        """
        各ユーザーのランキングの取得と保存
        """
        print "ランキング取得"
        start_time = time.time()
        rankings = self.get_rankings()
        r = redis.Redis(host=HOST, port=PORT, db=0)
        key = "rankings_" + str(self.user)
        top_k_songs = []
        for ranking in rankings:
            top_k_songs.append(ranking[1])
        print (top_k_songs[:10])
        print time.time() - start_time
        print "redisに保存"
        self._save_redis_top_k_songs(r, key, top_k_songs) # top_k保存
        self._save_redis_top_song(r, "top_song", str(self.user), top_k_songs[0]) # top_song保存{ "top_song": "user_id": song }
        self._save_top_matrix(r, self.user, top_k_songs[0])

    def get_rankings(self, rank = 5000):
        """
        ランキングを取得
        """
        self.get_not_learn_songs()
        self.songs = np.array(self.songs)
        # nonzeroのインデックス作成
        ixs = np.zeros(len(self.tag_map) + 2, dtype=np.int64)
        index = 0
        for tag, value in self.tag_map.items():
            ixs[index] = value
            index += 1
        user_index = self.labels["user="+str(self.user)]
        ixs[-2] = user_index
        rankings = []
        print "配列作成"
        for song_id in self.songs:
            song_label_name = "song="+str(song_id)
            song_index = self.labels[song_label_name]
            matrix = np.zeros(self.n)
            matrix[user_index] = 1.0
            matrix[song_index] = 1.0
            for index, tag_value in enumerate(self.song_tag_map[song_id]):
                matrix[self.tag_map[index]] = tag_value
            rankings.append((self.cy_fm.predict(matrix, str(song_id), ixs), song_id))

        rankings.sort()
        rankings.reverse()
        return rankings[:rank]

    def get_not_learn_songs(self):
        """
        まだ視聴していない楽曲のid配列を取得
        """
        print "未視聴の楽曲取得"
        q = models.Preference.objects.filter(user=self.user).values('song')
        results = models.Song.objects.exclude(id__in=q).values()
        tag_obj = models.Tag.objects.all()
        tags = [tag.name for tag in tag_obj]

        self.song_tag_map = {} # {song_id: List[tag_value]}
        self.songs = [] # List[song_id]
        for result in results:
            song_id = result['id']
            self.songs.append(song_id)
            self.song_tag_map.setdefault(song_id, [])
            for tag in tags:
                self.song_tag_map[song_id].append(result[tag])
    
    def arrange_user(self):
        """
        学習用のユーザーに関するデータを全て消す
        """
        print "ユーザー削除"
        learn_user_indexes = [] # 学習用のユーザーの配列のインデックス
        buffer_labels = [0] * self.n
        # [key]配列
        for key, index in self.labels.items():
            buffer_labels[index] = key
        
        new_index = 0
        new_labels = {}
        # 学習用のユーザーを取り除いた新しいラベル作成
        for index, key in enumerate(buffer_labels):
            if "user=u" in key:
                learn_user_indexes.append(index)
                continue
            new_labels[key] = new_index
            new_index += 1
        
        self.labels = new_labels
        self.n = len(self.labels)
        # cy_fmへセット
        self.cy_fm.set_n(self.n)
        adagrad_V = self.cy_fm.get_adagrad_V()
        adagrad_W = self.cy_fm.get_adagrad_W()
        self.V = np.delete(self.V, learn_user_indexes, 0)
        self.W = np.delete(self.W, learn_user_indexes)
        adagrad_V = np.delete(adagrad_V, learn_user_indexes, 0)
        adagrad_W = np.delete(adagrad_W, learn_user_indexes)
        tag_obj = models.Tag.objects.all()
        tags = [tag.name for tag in tag_obj]
        for index, tag in enumerate(tags):
            self.tag_map[index] = self.labels[tag]

        self.cy_fm.set_W(self.W)
        self.cy_fm.set_V(self.V)
        self.cy_fm.set_adagrad_V(adagrad_V)
        self.cy_fm.set_adagrad_W(adagrad_W)
    
    def _save_redis_top_k_songs(self, redis_obj, key, songs):
        """
        各ユーザーのtop_k_songs保存
        """
        redis_obj.delete(key)
        for song in songs:
            redis_obj.rpush(key, song)

    def _save_redis_top_song(self, redis_obj, key, field, song):
        """
        各ユーザーのtop_song保存
        """
        redis_obj.hset(key, field, song)

    def _save_top_matrix(self, redis_obj, user, song):
        """
        各ユーザーのtop_matrix保存
        """
        top_matrix = self.get_one_song_matrix(song)
        key = "top_matrix_"+ str(user)
        redis_obj.delete(key)
        for param in top_matrix:
            redis_obj.rpush(key, param)
    
    def set_W_and_V(self):
        """
        スムージング後、WとVを再セット
        """
        self.r = redis.Redis(host=HOST, port=PORT, db=0)
        self.get_W()
        self.get_V(len(self.W))

    def get_W(self):
        """
        Wの取得
        """
        W = self.r.lrange("W", 0, -1)
        self.W = self.change_array_into_float(W)

    def get_V(self, n):
        """
        Vの取得
        """
        self.V = self.get_two_dim_by_redis(self.r, "V_", n)

    def change_array_into_float(self, params):
        """
        np.ndarrayのtypeをfloatに変換
        """
        return np.array(params, dtype=np.float64)

    def get_two_dim_by_redis(self, redis_obj, pre_key, n):
        """
        二次元配列の取得
        """
        V = np.ones((self.K, n))
        for i in xrange(self.K):
            key = pre_key + str(i)
            v = redis_obj.lrange(key, 0, -1)
            V[i] = v
        V = np.array(V, dtype=np.float64)
        return V.T.copy(order='C')

