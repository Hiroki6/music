# -*- coding:utf-8 -*-

import numpy as np
import math
from FmSgd import fm_sgd_opt
import redis
from .. import models
import time
import sys
sys.dont_write_bytecode = True 
import os.path
BASE = os.path.dirname(os.path.abspath(__file__))

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

    def __init__(self, R, R_v, labels, targets, tag_map, seed=20, init_stdev=0.01):
        self.R = R #評価値行列
        self.labels = labels
        self.targets = targets # 教師配列
        self.tag_map = tag_map
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
        self.cy_fm = fm_sgd_opt.CyFmSgdOpt(self.R, self.R_v, self.targets, self.W, self.V, self.w_0, self.n, self.N, self.N_v, self.E, self.regs, l_rate, K, step, self.labels)
        # 学習
        self.cy_fm.learning()

    def save_top_k_ranking_all_user(self):
        """
        アプリのユーザーの未視聴のうちのtop10曲を予測し、redisに保存する
        """
        uniq_users = models.Preference.objects.all().values_list("user", flat=True).order_by("user").distinct()
        if len(uniq_users) == 0:
            return
        for user in uniq_users:
            self.user = user
            self.save_top_k_ranking_one_user()

    def save_top_k_ranking_one_user(self):

        self.get_matrixes_by_song()
        print "ランキング取得"
        start_time = time.time()
        rankings = self.get_rankings()
        r = redis.Redis(host='localhost', port=6379, db=0)
        key = "rankings_" + str(self.user)
        top_k_songs = []
        for ranking in rankings:
            top_k_songs.append(ranking[1])
        print time.time() - start_time
        print "redisに保存"
        self._save_redis_top_k_songs(r, key, top_k_songs) # top_k保存
        self._save_redis_top_song(r, "top_song", str(self.user), top_k_songs[0]) # top_song保存{ "top_song": "user_id": song }
        self._save_top_matrix(r, self.user, top_k_songs[0])

    def get_rankings(self, rank = 5000):
        """
        ランキングを取得
        """
        self.songs = np.array(self.songs)
        # nonzeroのインデックス作成
        ixs = np.zeros(len(self.tag_map) + 2, dtype=np.int64)
        index = 0
        for tag, value in self.tag_map.items():
            ixs[index] = value
            index += 1
        user_index = self.labels["user="+str(self.user)]
        ixs[-2] = user_index
        rankings = [(self.cy_fm.predict(matrix, str(song), ixs), song) for matrix, song in zip(self.matrixes, self.songs)]
        rankings.sort()
        rankings.reverse()
        return rankings[:rank]

    def get_matrixes_by_song(self):
        """
        楽曲からFM用の配列作成
        """
        self.get_not_learn_songs()
        print "配列作成"
        self.matrixes = np.zeros((len(self.song_tag_map), self.n))
        user_index = self.labels["user="+str(self.user)]
        for col, song_id in enumerate(self.songs):
            song_label_name = "song="+str(song_id)
            song_index = self.labels[song_label_name]
            self.matrixes[col][user_index] = 1.0
            self.matrixes[col][song_index] = 1.0
            for index, tag_value in enumerate(self.song_tag_map[song_id]):
                self.matrixes[col][self.tag_map[index]] = tag_value


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
    
    def _save_redis_top_k_songs(self, redis_obj, key, songs):
        for song in songs:
            redis_obj.rpush(key, song)

    def _save_redis_top_song(self, redis_obj, key, field, song):
        redis_obj.hset(key, field, song)

    def _save_top_matrix(self, redis_obj, user, song):
        top_matrix = self.get_one_song_matrix(song)
        for param in top_matrix:
            redis_obj.rpush("top_matrix_" + str(user), param)

    def get_one_song_matrix(self, song_id):

        top_matrix = np.zeros(self.n)
        song_index = self.labels["song="+str(song_id)]
        user_index = self.labels["user="+str(self.user)]
        top_matrix[user_index] = 1.0
        top_matrix[song_index] = 1.0
        for index, tag_value in enumerate(self.song_tag_map[song_id]):
            top_matrix[self.tag_map[index]] = tag_value

        return top_matrix
       
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

    def smoothing(self, smoothing_evaluate=False, rank = 10):
        """
        学習されていない楽曲のモデルに対してスムージングを行う
        """
        self.smoothing_evaluate = smoothing_evaluate
        start_time = time.time()
        self.get_divided_learning_songs()
        learn_song_norm = self.get_learn_song_norm()
        self.cy_fm.smoothing(self.not_learned_song_tag_map, self.learned_song_tag_map, learn_song_norm, rank)
        # スムージング後の値
        if smoothing_evaluate:
            r = redis.Redis(host='localhost', port=6379, db=1)
            self.save_W_and_V(r, "W_s", "V_s_")

        print time.time() - start_time

    def get_learn_song_norm(self):

        learn_song_norm = {}
        
        for learn_song, learn_tags in self.learned_song_tag_map.items():
            learn_song_norm[learn_song] = np.linalg.norm(learn_tags)

        return learn_song_norm

    def get_divided_learning_songs(self):
        """
        学習済みの楽曲と学習されていない楽曲に分ける{'song': [tags]}
        """
        tag_obj = models.Tag.objects.all()
        tags = [tag.name for tag in tag_obj]

        self.song_tag_map = {} # {song_id: List[tag_value]}
        learned_songs, not_learned_songs = self.divide_songs_obj()
        self.learned_song_tag_map = {} # {song_id: List[tag_value]}
        self.not_learned_song_tag_map = {} # {song_id: List[tag_value]}
        # 学習済みの楽曲の印象dict作成
        for song_obj in learned_songs:
            song_id = song_obj['id']
            self.learned_song_tag_map.setdefault(song_id, [])
            for tag in tags:
                self.learned_song_tag_map[song_id].append(song_obj[tag])
            self.learned_song_tag_map[song_id] = np.array(self.learned_song_tag_map[song_id])
        
        # 学習されていない楽曲の印象dict作成
        for song_obj in not_learned_songs:
            song_id = song_obj['id']
            self.not_learned_song_tag_map.setdefault(song_id, [])
            for tag in tags:
                self.not_learned_song_tag_map[song_id].append(song_obj[tag])
            self.not_learned_song_tag_map[song_id] = np.array(self.not_learned_song_tag_map[song_id])
       

    def divide_songs_obj(self):
        """
        学習済みのsong配列取得
        """
        learned_songs = []
        if self.smoothing_evaluate:
            r = redis.Redis(host='localhost', port=6379, db=1)
            learned_songs = r.lrange("train_songs", 0, -1)
            learned_songs = map(int, learned_songs)
            not_learned_songs = r.lrange("validation_songs", 0, -1)
            not_learned_songs = map(int, not_learned_songs)
            # スムージング前の楽曲の保存
            #self.save_W_and_V(r, "W", "V_")
            # スムージング対象の楽曲のインデックス保存
            self.save_smoothing_labels(r, not_learned_songs)
            not_learned_songs_obj = models.Song.objects.filter(id__in=not_learned_songs).values()
        else:
            with open(os.path.join(BASE, "../data_10/uniq_songs.csv")) as f:
                for line in f:
                    song = line.replace("\n","").split(",")[0]
                    learned_songs.append(int(song))
        
            preference_songs = models.Preference.objects.all().values("song").distinct()
            for preference_song in preference_songs:
                song = preference_song["song"]
                if song not in learned_songs:
                    learned_songs.append(song)
            not_learned_songs_obj = models.Song.objects.exclude(id__in=learned_songs).values()

        learned_songs_obj = models.Song.objects.filter(id__in=learned_songs).values()
        print len(learned_songs_obj)
        print len(not_learned_songs_obj)

        return learned_songs_obj, not_learned_songs_obj

    def save_smoothing_labels(self, redis_obj, not_learned_songs):
        """
        スムージングの対象インデックスのredisへの保存
        """
        for song in not_learned_songs:
            index = self.labels["song=" + str(song)]
            redis_obj.rpush("smoothing_songs", index)

    def save_W_and_V(self, redis_obj, w_key, v_pre_key):
        """
        WとVの保存
        """
        self.cy_fm.save_one_dim_array(redis_obj, w_key, self.W)
        self.cy_fm.save_two_dim_array(redis_obj, v_pre_key, self.V)
