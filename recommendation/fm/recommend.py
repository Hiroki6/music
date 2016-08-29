# -*- coding:utf-8 -*-

import numpy as np
import redis
from Recommend import cy_recommend as cyFm
from .. import models
import time
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
        self.cy_fm = cyFm.CyRecommendFm(self.w_0, self.W, self.V, self.adagrad_w_0, self.adagrad_W, self.adagrad_V, self.regs, len(self.W), K, 0.005, self.labels)

    def get_range_params(self):
        """
        redisに保存されているパラメータを取得
        """
        r = redis.Redis(host=HOST, port=PORT, db=DB)
        r.set_response_callback("lrange", float)
        s = time.time()
        self.w_0 = self._get_param(r, "bias", "w_0")
        start_time = time.time()
        self.W = self._get_one_dim_params(r, "W", "float")
        print "W読み込みタイム: %.5f" % (time.time() - start_time)
        start_time = time.time()
        self.V = self._get_two_dim_params(r, "V_")
        print "V読み込みタイム: %.5f" % (time.time() - start_time)
        self.regs = self._get_one_dim_params(r, "regs")
        self.adagrad_w_0 = self._get_param(r, "bias", "adagrad")
        self.adagrad_W = self._get_one_dim_params(r, "adagrad_W")
        self.adagrad_V = self._get_two_dim_params(r, "adagrad_V_")
        self._get_labels(r)
        self._get_tag_map(r)
        print "redis読み込みタイム: %.5f" % (time.time() - s)
  
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

        V = np.ones((self.K, len(self.W)))
        for i in xrange(self.K):
            key = pre_key + str(i)
            v = redis_obj.lrange(key, 0, -1)
            #v = np.array(v, dtype=np.float64)
            V[i] = v
        # copy(order='C')によってC-連続アレイに変換する
        V = np.array(V, dtype=np.float64)
        return V.T.copy(order='C')

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
        return array

    def get_rankings(self, rank = 100):
        """
        ランキングを取得
        """
        rankings = [(self.cy_fm.predict(matrix, str(song), self.ixs), song) for matrix, song in zip(self.matrixes, self.songs)]
        rankings.sort()
        rankings.reverse()
        return rankings[:rank]

    def save_top_song(self):
        """
        １位の楽曲の楽曲ID、配列をredisに保存
        """
        print "１位の楽曲取得"
        start_time = time.time()
        rankings = self.get_rankings()
        print time.time() - start_time
        print "楽曲をredisに保存"
        r = redis.Redis(host=HOST, port=PORT, db=DB)
        recommended_song_obj = models.RecommendSong.objects.filter(user=self.user)
        recommended_songs = [song.song_id for song in recommended_song_obj]
        print rankings[0][1]
        for ranking in rankings:
            if ranking[1] not in recommended_songs:
                top_song = ranking[1]
                break
        #top_song = rankings[0][1] if self.top_song != rankings[0][1] else rankings[1][1]
        print top_song
        self._save_scalar(r, "top_song", str(self.user), top_song)
        self._save_top_matrix(r, self.user, top_song)

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
        top_k_songs = self._get_top_k_songs()
        results = models.Song.objects.exclude(id__in=q).filter(id__in=top_k_songs).values()
        tag_obj = models.Tag.objects.all()
        tags = [tag.name for tag in tag_obj]

        self.song_tag_map = {} # {song_id: List[tag_value]}
        self.songs = [] # List[song_id]
        result_length = len(results[0])
        for result in results:
            song_id = result['id']
            self.songs.append(song_id)
            self.song_tag_map.setdefault(song_id, [])
            for tag in tags:
                self.song_tag_map[song_id].append(result[tag])
       

    def get_matrixes_by_song(self):
        """
        未視聴の楽曲配列作成
        """
        print "未視聴の楽曲配列作成"
        self.get_not_learn_songs()
        self.matrixes = np.zeros((len(self.song_tag_map), len(self.W)))
        user_index = self.labels["user="+str(self.user)]
        for col, song_id in enumerate(self.songs):
            song_label_name = "song="+str(song_id)
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
        self.feedback_matrix = np.array(self.top_matrix)
        song_label_name = "song=" + str(self.top_song)
        song_index = self.labels[song_label_name]
        self.feedback_matrix[song_index] = 0.0
        self.top_matrix[song_index] = 0.0
        alpha = 0.1 if self.plus_or_minus == 1 else -0.1 # フィードバックによって+-を分ける
        user_index = self.labels["user="+str(self.user)]
        for i, tag in enumerate(self.tags):
            index = tag[0]
            self.feedback_matrix[self.tag_map[index]] += alpha/self.feedback_matrix[self.tag_map[index]]

    def get_tags_by_feedback(self, feedback):
        """
        feedback: 1~10
        """
        feedback = int(feedback)
        if(feedback <= 4):
            self.plus_or_minus = 1
        else:
            self.plus_or_minus = -1
            feedback -= 5
        feedback += 1
        tags = models.Tag.objects.filter(cluster__id=feedback)
        self.tags = [(tag.id-1, tag.name) for tag in tags]

    def relearning(self, feedback):
        r = redis.Redis(host=HOST, port=PORT, db=DB)
        start_time = time.time()
        self.top_matrix = self._get_one_dim_params(r, "top_matrix_" + str(self.user), "float") # 前回推薦の楽曲の特徴ベクトル配列取得
        self._get_top_song_by_redis(r) # self.top_songに前回推薦の楽曲のID格納
        self.create_feedback_matrix(feedback) # フィードバック用の配列取得
        print "配列構築タイム: %.5f" % (time.time() - start_time)
        start_time = time.time()
        self.cy_fm.relearning(self.top_matrix, self.feedback_matrix) # 再学習
        print "再学習タイム: %.5f" % (time.time() - start_time)
        self._set_ixs()
        start_time = time.time()
        self._save_redis_relearning() # 更新されたVとadagrad_VをDBに保存
        print "redis更新タイム: %.5f" % (time.time() - start_time)
        self.get_matrixes_by_song()
        self.save_top_song()

    def _set_ixs(self):
    
        print "set ixs"
        self.ixs = np.zeros(len(self.tag_map) + 2, dtype=np.int64)
        index = 0
        for tag, value in self.tag_map.items():
            self.ixs[index] = value
            index += 1
        user_index = self.labels["user="+str(self.user)]
        self.ixs[-2] = user_index

    def save_redis(self):
        """
        パラメータのredisへの保存
        """
        r = redis.Redis(host=HOST, port=PORT, db=DB)
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

    def _save_redis_relearning(self):
        """
        再学習の時のredisの保存
        まず、既存のVとadagrad_Vを削除してから保存する
        """
        print "redis更新"
        r = redis.Redis(host=HOST, port=PORT, db=DB)
        self.adagrad_V = self.cy_fm.get_adagrad_V()
        self._update_V_array(r, "V_", "adagrad_V_")

    def _update_V_array(self, redis_obj, v_pre_key, adagrad_v_pre_key):
        """
        既存のVとadagrad_Vの削除
        """
        for f in xrange(self.K):
            v_key = v_pre_key + str(f)
            adagrad_v_key = adagrad_v_pre_key + str(f)
            for ixs in self.ixs:
                redis_obj.lset(v_key, ixs, self.V[ixs][f])
                redis_obj.lset(adagrad_v_key, ixs, self.adagrad_V[ixs][f])

    def _save_scalar(self, redis_obj, field, key, param):
        redis_obj.hset(field, key, param)

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
    
    def _get_top_song_by_redis(self, redis_obj):
        top_song = redis_obj.hget("top_song", str(self.user))
        self.top_song = int(top_song)

    def get_one_song_matrix(self, song_id):

        top_matrix = np.zeros(len(self.W))
        song_index = self.labels["song="+str(song_id)]
        user_index = self.labels["user="+str(self.user)]
        top_matrix[user_index] = 1.0
        top_matrix[song_index] = 1.0
        for index, tag_value in enumerate(self.song_tag_map[song_id]):
            top_matrix[self.tag_map[index]] = tag_value

        return top_matrix

    def _save_top_matrix(self, redis_obj, user, song):
        top_matrix = self.get_one_song_matrix(song)
        key = "top_matrix_" + str(user)
        redis_obj.delete(key)
        for param in top_matrix:
            redis_obj.rpush(key, param)

    def _get_top_k_songs(self):
        r = redis.Redis(host=HOST, port=PORT, db=DB)
        key = "rankings_" + str(self.user)
        top_k_songs = r.lrange(key, 0, -1)
        top_k_songs = np.array(top_k_songs, dtype=np.int64)
        return top_k_songs

