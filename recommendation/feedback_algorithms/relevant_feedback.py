# -*- coding:utf-8 -*-

"""
印象語検索における適合性フィードバックによるモデルの学習
"""

import numpy as np
import redis
import common_functions as common
import redis_functions as redis_f
from RelevantFeedback import cy_relevant_feedback as cy_rf
import sys
from recommendation import models
import codecs
import random

HOST = 'localhost'
PORT = 6379
DB = 2

emotion_map = {1: "pop", 2: "ballad", 3: "rock"}

class RelevantFeedback(object):
    """
    適合性フィードバックによるオンライン学習クラス
    """
    def __init__(self, user, situation, emotions, cf_obj):
        self.user = user
        self.situation = situation
        self._get_params_by_redis()
        self._get_now_feedback()
        self.emotions = map(int, emotions)
        self._set_emotion_dict()
        self.cy_obj = cy_rf.CyRelevantFeedback(self.W, self.bias, 43)
        self.cf_obj = cf_obj

    def _get_params_by_redis(self):
        self.r = redis_f.get_redis_obj(HOST, PORT, DB)
        key =  "W_" + self.user
        self.W = redis_f.get_one_dim_params(self.r, key)
        self.bias = redis_f.get_scalar(self.r, "bias", self.user)

    def _get_learning_data(self, learning_method):
        """
        学習データの取得
        """
        relevant_datas = models.EmotionRelevantSong.objects.order_by("id").filter(user_id=int(self.user), situation=self.situation).values()
        self.song_relevant = {} # {song_id: relevant_type}
        if learning_method == "online":
            relevant_datas = relevant_datas.reverse()
            self.song_relevant[relevant_datas[0]["song_id"]] = relevant_datas[0]["relevant_type"]
        else:
            for relevant_data in relevant_datas:
                self.song_relevant[relevant_data["song_id"]] = relevant_data["relevant_type"]

    def _get_now_feedback(self):
        """
        現在のフィードバック取得
        """
        relevant_datas = models.EmotionRelevantSong.objects.order_by("id").filter(user_id=int(self.user), situation=self.situation).values()
        self.now_feedback = relevant_datas[len(relevant_datas)-1]["relevant_type"]

    def set_learning_params(self, l_rate, beta, learning_method = "online"):
        """
        学習パラメータの設定
        """
        self.beta = beta
        self.cy_obj.set_learning_params(l_rate, beta)
        self._get_learning_data(learning_method)
        self._set_listening_songs()

    def _set_listening_songs(self):

        self.songs, self.song_tag_map = self.cf_obj.get_listening_songs(self.emotion_map, self.emotions)

    def fit(self):
        """
        CyRelevantFeedbackクラスを用いたモデルの学習
        """
        error = 0
        for i in xrange(10000):
            before_error = error
            #for song_id, relevant_type in self.song_relevant.items():
            #    self.cy_obj.fit(self.song_tag_map[song_id], relevant_type)
            song_id = random.choice(self.song_relevant.keys())
            relevant_type = self.song_relevant[song_id]
            if relevant_type == 0:
                continue
            self.cy_obj.fit(self.song_tag_map[song_id], relevant_type)
            error = self._calc_all_error()
            if error < 0.0001 or abs(error - before_error) < 0.000001:
                print "iterations %d" % (i)
                print "final error %.8f" % (error)
                self.bias = self.cy_obj.get_bias()
                break
        for song_id, relevant_type in self.song_relevant.items():
            if relevant_type == 0:
                continue
            print "target: %.1f" % (relevant_type)
            print "predict: %.8f" % (self.cy_obj.predict(self.song_tag_map[song_id]))
        self._update_params_into_redis()

    def _calc_all_error(self):
        """
        全ての誤差を計算する
        """
        error = 0.0
        for song_id, relevant_type in self.song_relevant.items():
            error += pow(self.cy_obj.calc_error(self.song_tag_map[song_id], relevant_type), 2)
        error += self.beta * np.linalg.norm(self.W)

        return error

    def get_init_songs(self):
        songs = redis_f.get_init_songs_by_redis("init_songs_" + str(self.user))
        return songs[:1]

    def get_top_k_songs(self, k=1):
        """
        検索対象の印象語に含まれている楽曲から回帰値の高いk個の楽曲を取得する
        """
        # 初期検索の時
        song_map = self.cf_obj.get_song_and_cluster()
        songs, song_tag_map = self.cf_obj.get_not_listening_songs(self.emotion_map, self.emotions)
        rankings = [(self.cy_obj.predict(tags), song_id) for song_id, tags in song_tag_map.items()]
        self.cf_obj.listtuple_sort_reverse(rankings)
        self.cf_obj.write_top_k_songs_relevance("relevant_k_song.txt", rankings[:10], self.emotion_map, self.emotions, self.now_feedback)
        self._save_top_k_songs(rankings[:5])
        return rankings[:k]

    def _update_params_into_redis(self):
        redis_f.update_redis_key(self.r, "W_" + self.user, self.W)
        redis_f.save_scalar(self.r, "bias", self.user, self.bias)

    def _set_emotion_dict(self):
        self.emotion_map = {}
        tags = models.Tag.objects.all()
        for tag in tags:
            if tag.search_flag:
                self.emotion_map[tag.id] = tag.name

    def _save_top_k_songs(self, rankings):
        """
        top_kの楽曲をredisに保存
        """
        key = "top_k_songs_" + self.user
        redis_f.delete_redis_key(self.r, key)
        for ranking in rankings:
            song_id = ranking[1]
            redis_f.rpush_redis_key(self.r, key, song_id)

class RelevantFeedbackRandom(RelevantFeedback):
    """
    適合性フィードバックによるオンライン学習クラス
    状況のみの検索を行うため、emotionsは用いない
    """
    def __init__(self, user, situation, cf_obj):
        RelevantFeedback.__init__(self, user, situation, [], cf_obj)

    def get_top_k_songs(self, k=1):
        """
        検索対象の印象語に含まれている楽曲から回帰値の高いk個の楽曲を取得する
        """
        # 初期検索の時
        song_map = self.cf_obj.get_song_and_cluster()
        songs, song_tag_map = self.cf_obj.get_not_listening_songs()
        rankings = [(self.cy_obj.predict(tags), song_id) for song_id, tags in song_tag_map.items()]
        self.cf_obj.listtuple_sort_reverse(rankings)
        self.cf_obj.write_top_k_songs_relevance("random_relevant_k_song.txt", rankings[:10], {}, [], self.now_feedback)
        self._save_top_k_songs(rankings[:5])
        #self._save_top_k_songs_now_order(rankings[:5])
        return rankings[:k]

    def _save_top_k_songs_now_order(self, rankings):
        """
        現在の順番のインタラクションの時のtop_k_songsをredisに保存する
        """
        count = self.cf_obj.get_now_order(self.situation, 0)
        key = "top_k_songs_" + self.user + "_" + str(count)
        redis_f.delete_redis_key(self.r, key)
        for ranking in rankings:
            song_id = ranking[1]
            redis_f.rpush_redis_key(self.r, key, song_id)

    def _set_listening_songs(self):

        self.songs, self.song_tag_map = self.cf_obj.get_listening_songs()

