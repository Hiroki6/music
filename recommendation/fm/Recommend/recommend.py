# -*- coding:utf-8 -*-

import numpy as np
import redis
import cy_recommend as cyFm
import sys
import MySQLdb

HOST = 'localhost'
PORT = 6379
DB = 0

class RecommendFm(object):
    def __init__(self, user, K):
        self.K = K
        self.user = user
        self.get_range_params()
        self.cy_fm = cyFm.CyRecommendFm(self.w_0, self.W, self.V, self.adagrad_w_0, self.adagrad_W, self.adagrad_V, self.regs, len(self.W), K, 0.005)
        self.get_not_learn_songs()

    def get_range_params(self):
        """
        redisに保存されているパラメータを取得
        """
        r = redis.Redis(host=HOST, port=PORT, db=DB)
        self.w_0 = self._get_param(r, "bias", "w_0")
        self.W = self._get_one_dim_params(r, "W", "float")
        self.V = self._get_two_dim_params(r, "V_")
        self.regs = self._get_one_dim_params(r, "regs")
        self.adagrad_w_0 = self._get_param(r, "bias", "adagrad")
        self.adagrad_W = self._get_one_dim_params(r, "adagrad_W")
        self.adagrad_V = self._get_two_dim_params(r, "adagrad_V_")
        self.labels = self._get_one_dim_params(r, "labels", "str")
        self._get_tag_map(r)
  
    def _get_tag_map(self, redis_obj):

        self.tag_map = {}
        fields = redis_obj.hkeys("tag_map")
        for field in fields:
            value = redis_obj.hget("tag_map", field)
            self.tag_map[int(field)] = int(value)

    def _get_one_dim_params(self, redis_obj, key, dtype="float"):

        params = redis_obj.lrange(key, 0, -1)
        if dtype == "float":
            params = np.array(params, dtype=np.float64)
        return params

    def _get_param(self, redis_obj, hash_key, key):

        param = redis_obj.hget(hash_key, key)
        param = float(param)
        return param

    def _get_two_dim_params(self, redis_obj, pre_key):

        V = np.ones((len(self.W), self.K))
        for i in xrange(len(self.W)):
            key = pre_key + str(i)
            v = redis_obj.lrange(key, 0, -1)
            v = np.array(v, dtype=np.float64)
            V[i] = v
        return V

    def change_type_into_float(self, array):
        """
        配列をfloat型のnumpy配列に変換
        """
        array = np.array(array, dtype=np.float64)
        #array = array.astype(np.float64_t)
        return array

    def get_rankings(self, rank = 100):
        """
        ランキングを取得
        """
        rankings = [(self.cy_fm.predict(matrix), song) for matrix, song in zip(self.matrixes, self.songs)]
        rankings.sort()
        rankings.reverse()
        return rankings[:rank]

    def get_top_song(self):
        """
        １位の楽曲の予測値、楽曲ID、配列を取得
        """
        top_value = -sys.maxint
        top_matrix = self.matrixes[0]
        top_song = self.songs[0]
        for matrix, song in zip(self.matrixes, self.songs):
            predict_value = self.cy_fm.predict(matrix)
            if top_value < predict_value:
                top_value = predict_value
                top_matrix = matrix
                top_song = song

        return top_value, top_song, top_matrix

    def get_not_learn_songs(self):
        """
        まだ視聴していない楽曲のid配列を取得
        """
        self.connect_db()
        sql = "select song_tag.* from recommendation_song as song join recommendation_songtag as song_tag on song.id = song_tag.song_id where song.id not in (select song_id from recommendation_preference where user_id = '%s')" % (self.user)
        self.cursor.execute(sql)
        results = self.cursor.fetchall()
        sql = "select name from recommendation_tag"
        self.cursor.execute(sql)
        tag_results = self.cursor.fetchall()
        tags = []
        for tag_result in tag_results:
            tags.append(tag_result[0])

        self.song_tag_map = {}
        self.songs = []
        result_length = len(results[0])
        for result in results:
            song_id = result[0]
            self.songs.append(song_id)
            self.song_tag_map.setdefault(song_id, [])
            for tag_index in xrange(1,result_length-1):
                self.song_tag_map[song_id].append(result[tag_index])
        
        self.close_db()

    def get_matrixes_by_song(self):
        """
        楽曲からFM用の配列作成
        """
        self.get_not_learn_songs()
        self.matrixes = np.zeros((len(self.song_tag_map), len(self.W)))
        user_index = self.labels.index("user="+str(self.user))
        for col, song_id in enumerate(self.songs):
            song_label_name = "song="+str(song_id)
            if song_label_name in self.labels:
                song_index = self.labels.index(song_label_name)
                self.matrixes[col][user_index] = 1.0
                self.matrixes[col][song_index] = 1.0
                for index, tag_value in enumerate(self.song_tag_map[song_id]):
                    self.matrixes[col][self.tag_map[index]] = tag_value

    def relearning(self, top_matrix, feedback_matrix, feature_indexes):
        feature_num = len(feature_indexes)
        self.cy_fm.relearning(top_matrix, feedback_matrix, feature_indexes, feature_num)
        self.save_redis()

    def save_redis(self):
        """
        パラメータのredisへの保存
        """
        r = redis.Redis(host='localhost', port=6379, db=1)
        """
        一度全て消す
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
        self.save_scalar("bias", "adagrad", adagrad_w_0)
        # adagrad_Wの保存
        self.save_one_dim_array(r, "adagrad_W", adagrad_W)
        # adagrad_Vの保存
        self.save_two_dim_array(r, "adagrad_V_", adagrad_V)

    def save_scalar(self, redis_obj, table, key, param):
        redis_obj.hset(table, key, param)

    def save_one_dim_array(self, redis_obj, key, params):
        for param in params:
            redis_obj.rpush(key, param)

    def save_two_dim_array(self, redis_obj, pre_key, params):
        for i in xrange(len(params)):
            key = pre_key + str(i)
            for param in params[i]:
                redis_obj.rpush(key, param)

    def connect_db(self):
        self.connection = MySQLdb.connect(host="localhost", db="music", user="fujino", passwd="fujino", charset="utf8")
        self.cursor = self.connection.cursor()

    def close_db(self):
        self.cursor.close()
        self.connection.close()

