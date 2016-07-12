# -*- coding:utf-8 -*-

import numpy as np
import redis
from Recommend import cy_recommend as cyFm
import sys
from .. import models
import sys
sys.dont_write_bytecode = True 

HOST = 'localhost'
PORT = 6379
DB = 0

class RecommendFm(object):
    def __init__(self, user, K):
        self.K = K
        self.user = user
        self.get_range_params()
        self.cy_fm = cyFm.CyRecommendFm(self.w_0, self.W, self.V, self.adagrad_w_0, self.adagrad_W, self.adagrad_V, self.regs, len(self.W), K, 0.005)

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
        self._get_labels(r)
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

    def _get_labels(self, redis_obj):
    
        self.labels = {}
        keys = redis_obj.lrange("label_keys", 0, -1)
        values = redis_obj.lrange("label_values", 0, -1)
        values = np.array(values, dtype=np.int)
        for key, value in zip(keys, values):
            self.labels[key] = value

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
        top_song_obj = Song.objects.filter(id=top_song)
        return top_song_obj

    def get_top_song_cython(self):

        self.songs = np.array(self.songs)
        top_song = self.cy_fm.get_top_song(self.matrixes, self.songs)
        top_song_obj = Song.objects.filter(id=top_song)
        return top_song_obj

    def get_not_learn_songs(self):
        """
        まだ視聴していない楽曲のid配列を取得
        """
        q = models.Preference.objects.filter(user=self.user).values('song')
        results = models.SongTag.objects.exclude(song__in=q).values()
        tag_obj = models.Tag.objects.all()
        tags = [tag.name for tag in tag_obj]

        self.song_tag_map = {} # {song_id: List[tag_value]}
        self.songs = [] # List[song_id]
        result_length = len(results[0])
        for result in results:
            song_id = result['song_id']
            self.songs.append(song_id)
            self.song_tag_map.setdefault(song_id, [])
            for tag in tags:
                self.song_tag_map[song_id].append(result[tag])
       

    def get_matrixes_by_song(self):
        """
        楽曲からFM用の配列作成
        """
        self.get_not_learn_songs()
        self.matrixes = np.zeros((len(self.song_tag_map), len(self.W)))
        user_index = self.labels["user="+str(self.user)]
        for col, song_id in enumerate(self.songs):
            song_label_name = "song="+str(song_id)
            if song_label_name in self.labels:
                song_index = self.labels[song_label_name]
                self.matrixes[col][user_index] = 1.0
                self.matrixes[col][song_index] = 1.0
                for index, tag_value in enumerate(self.song_tag_map[song_id]):
                    self.matrixes[col][self.tag_map[index]] = tag_value

    def create_feedback_matrix(self, feedback):
        """
        特定のユーザーによるフィードバックを反映させた楽曲の特徴ベクトル生成
        @returns(top_matrix): 推薦された楽曲配列の楽曲の部分だけ0にしたもの
        @returns(feedback_matrix): フィードバックを受けたタグの部分だけ値を大きくしたもの
        """
        self.get_tags_by_feedback(feedback)
        self.feature_indexes = np.zeros(1+len(self.tags),dtype=np.int)
        self.feedback_matrix = np.array(self.top_matrix)
        song_label_name = "song=" + str(self.top_song)
        song_index = self.labels[song_label_name]
        self.feedback_matrix[song_index] = 0.0
        self.top_matrix[song_index] = 0.0
        alpha = 0.05 if self.plus_or_minus == 1 else -0.05 # フィードバックによって+-を分ける
        user_index = self.labels["user="+str(self.user)]
        self.feature_indexes[0] = user_index
        for i, tag in enumerate(self.tags):
            index = tag[0]
            self.feature_indexes[i+1] = self.tag_map[index]
            self.feedback_matrix[self.tag_map[index]] += alpha/self.feedback_matrix[self.tag_map[index]]

    def get_tags_by_feedback(self, feedback):
        """
        feedback: 1~10
        """
        feedback = int(feedback)
        if(feedback <= 5):
            self.plus_or_minus = 1
        else:
            self.plus_or_minus = -1
        tags = models.Tag.objects.filter(cluster__id=feedback)
        self.tags = [(tag.id-1, tag.name) for tag in tags]

    def relearning(self, feedback):
        self.create_feedback_matrix(feedback)
        feature_num = len(self.feature_indexes)
        self.cy_fm.relearning(self.top_matrix, self.feedback_matrix, self.feature_indexes, feature_num)
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
        w_0 = self.cy_fm.get_w_0()
        # w_0の保存
        self._save_scalar(r, "bias", "w_0", w_0)
        # Wの保存
        self._save_one_dim_array(r, "W", self.W)
        # Vの保存
        self._save_two_dim_array(r, "V_", self.V)

        """
        regsの保存
        """
        self._save_one_dim_array(r, "regs", self.regs)
        
        """
        adagradの保存
        """
        adagrad_w_0 = self.cy_fm.get_adagrad_w_0()
        adagrad_W = self.cy_fm.get_adagrad_W()
        adagrad_V = self.cy_fm.get_adagrad_V()
        # adagrad_w_0の保存
        self._save_scalar("bias", "adagrad", adagrad_w_0)
        # adagrad_Wの保存
        self._save_one_dim_array(r, "adagrad_W", adagrad_W)
        # adagrad_Vの保存
        self._save_two_dim_array(r, "adagrad_V_", adagrad_V)
        self._save_tag_map(r)
        self._save_labels(r)

    def _save_scalar(self, redis_obj, table, key, param):
        redis_obj.hset(table, key, param)

    def _save_one_dim_array(self, redis_obj, key, params):
        for param in params:
            redis_obj.rpush(key, param)

    def _save_two_dim_array(self, redis_obj, pre_key, params):
        for i in xrange(len(params)):
            key = pre_key + str(i)
            for param in params[i]:
                redis_obj.rpush(key, param)
    
    def _save_tag_map(self, r):

        for key, value in self.tag_map.items():
            r.hset("tag_map", key, value)

    def _save_labels(self, redis_obj):

        for key, value in self.labels.items():
            redis_obj.rpush("label_keys", key)
            redis_obj.rpush("label_values", value)

