# -*- coding:utf-8 -*-

"""
スムージングを行う
"""
import numpy as np
import redis
from math import sqrt
from .. import models
from Smoothing import cy_smoothing
import os
BASE = os.path.dirname(os.path.abspath(__file__))

class SmoothingFm():
    """
    parameters
    K: Vの次元
    evaluate_smoothing: 交差検定用かどうか
    W: 学習済みのtrain配列
    s_W: スムージング用の重み配列: K+1 * 43
    s_w0: スムージング用のバイアス: K+1
    """
    def __init__(self, K, evaluation_flag = False):
        self.K = K
        self.evaluation_flag = evaluation_flag
        self.get_redis_obj()
        self.get_params()
        self.get_labels()

    def learning(self, l_rate = 0.005, beta = 0.1):
        self.get_divided_learning_songs()
        #self.s_W = np.random.rand(self.K+1, 43)
        np.random.seed(seed=20)
        self.s_W = np.random.normal(scale=0.001,size=(self.K+1, 43))
        self.s_w0 = np.zeros(self.K+1)
        self.cy_s = cy_smoothing.CySmoothing(self.s_W, self.s_w0, self.W, self.V, self.K+1, self.learned_song_tag_map)
        self.cy_s.learning(l_rate, beta)

    def get_redis_obj(self):

        db = 0
        if self.evaluation_flag:
            db = 1

        self.r = redis.Redis(host="localhost", port=6379, db=db)

    def get_params(self):

        self.get_W()
        self.get_V(len(self.W))
    
    def get_W(self):

        W = self.r.lrange("W", 0, -1)
        self.W = self.change_array_into_float(W)

    def get_V(self, n):

        self.V = self.get_two_dim_by_redis(self.r, "V_", n)

    def change_array_into_float(self, params):

        return np.array(params, dtype=np.float64)

    def get_two_dim_by_redis(self, redis_obj, pre_key, n):

        V = np.ones((self.K, n))
        for i in xrange(self.K):
            key = pre_key + str(i)
            v = redis_obj.lrange(key, 0, -1)
            V[i] = v
        V = np.array(V, dtype=np.float64)
        return V.T.copy(order='C')
    
    def get_divided_learning_songs(self):
        """
        学習済みの楽曲と学習されていない楽曲に分ける{'song': [tags]}
        """
        tag_obj = models.Tag.objects.all()
        tags = [tag.name for tag in tag_obj]

        learned_songs_obj, not_learned_songs_obj = self.divide_songs_obj()

        # 学習済みの楽曲の印象dict作成
        # {song_id: List[tag_value]}
        self.learned_song_tag_map = self.transform_song_tag_map(learned_songs_obj, tags)
        # 学習されていない楽曲の印象dict作成
        # {song_id: List[tag_value]}
        self.not_learned_song_tag_map = self.transform_song_tag_map(not_learned_songs_obj, tags)


    def transform_song_tag_map(self, songs_obj, tags):
    
        song_tag_map = {}
        for song_obj in songs_obj:
            song_id = song_obj['id']
            song_index = self.labels["song=" + str(song_id)]
            song_tag_map.setdefault(song_index, [])
            for tag in tags:
                song_tag_map[song_index].append(song_obj[tag])
            song_tag_map[song_index] = np.array(song_tag_map[song_index])

        return song_tag_map

    def divide_songs_obj(self):
        """
        learned_songs: 学習済みのsong配列
        not_learned_songs: 学習されていないsong配列
        """
        learned_songs = []
        if self.evaluation_flag:
            learned_songs = self.r.lrange("train_songs", 0, -1)
            learned_songs = map(int, learned_songs)
            not_learned_songs = self.r.lrange("validation_songs", 0, -1)
            not_learned_songs = map(int, not_learned_songs)
            # スムージング前の楽曲の保存
            #self.save_W_and_V("W", "V_")
            # スムージング対象の楽曲のインデックス保存
            self.save_smoothing_labels(not_learned_songs)
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

        return learned_songs_obj, not_learned_songs_obj

    def save_smoothing_labels(self, not_learned_songs):
        """
        スムージングの対象インデックスのredisへの保存
        """
        self.r.delete("smoothing_songs")
        for song in not_learned_songs:
            index = self.labels["song=" + str(song)]
            self.r.rpush("smoothing_songs", index)

    def get_labels(self):
    
        r = redis.Redis(host="localhost", port=6379, db=0)
        self.labels = {}
        keys = r.lrange("label_keys", 0, -1)
        values = r.lrange("label_values", 0, -1)
        values = np.array(values, dtype=np.int)
        for key, value in zip(keys, values):
            self.labels[key] = value

    def smoothing(self):
        """
        スムージングを行う
        """
        for song_index, song_tags in self.not_learned_song_tag_map.items():
            """
            WとVの更新
            """
            self.W[song_index], self.V[song_index] = self.cy_s.regression_all_params(song_tags)
        # 交差検定の場合は*_sに保存
        if self.evaluation_flag:
            self.save_W_and_V("W_s", "V_s_")
        # 交差検定でない場合は上書き
        else:
            self.save_W_and_V("W", "V_")

    def save_W_and_V(self, w_key, v_pre_key):
        """
        WとVの保存
        """
        # keyのデータベースを削除する
        self._delete_scalar_key(w_key)
        self._delete_one_dim_key(v_pre_key)
        # 保存
        self._save_one_dim_array(w_key, self.W)
        self._save_two_dim_array(v_pre_key, self.V)

    def _save_one_dim_array(self, key, params):
        for param in params:
            self.r.rpush(key, param)

    def _save_two_dim_array(self, pre_key, params):
        for i in xrange(self.K):
            key = pre_key + str(i)
            for param in params.T[i]:
                self.r.rpush(key, param)

    def _delete_scalar_key(self, key):

        self.r.delete(key)

    def _delete_one_dim_key(self, pre_key):

        for i in xrange(self.K):
            key = pre_key + str(i)
            self.r.delete(key)
