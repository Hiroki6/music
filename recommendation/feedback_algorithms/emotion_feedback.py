# -*- coding:utf-8 -*-

"""
印象語検索における印象語フィードバックによるモデルの学習
"""

import numpy as np
import redis
import common_functions as common
from EmotionFeedback import cy_emotion_feedback as cy_ef
import sys
from recommendation import models
import math
import random

HOST = 'localhost'
PORT = 6379
DB = 3

emotion_map = {1: "pop", 2: "ballad", 3: "rock"}

# 境界条件のmap
bound_map = {1: 0.015283, 2: 0.030881, 3: 0.019013}
ave_map = {1: 0.125574, 2: 0.128966, 3: 0.099840}
max_map = {1: 0.16459, 2: 0.19948, 3: 0.14737}
min_map = {1: 0.07261, 2: 0.06131, 3: 0.05837}

class EmotionBaseline(object):
    """
    印象語フィードバックのベースライン
    フィードバックを受けた楽曲よりも印象値が高い楽曲を推薦する
    モデルは持たずにランダムに楽曲を検索し、そこからフィードバックを受けて新しい楽曲を推薦していく
    user: ログインユーザーID
    emotions: 検索語に選択した印象語配列
    """
    def __init__(self, user, emotions):
        self.user = user
        self.emotions = map(int, emotions)

    def _save_top_song(self):
        """
        top_songの保存
        """
        common.delete_redis_key(self.r, "top_matrix_" + self.user)
        common.save_scalar(self.r, "top_song", self.user, self.top_song)
        common.save_one_dim_array(self.r, "top_matrix_"+self.user, self.top_matrix)

    def get_top_song(self):
        """
        推薦する楽曲の取得
        """
        self.top_song = self.bound_songs[0]
        self.top_matrix = self.bound_song_tag_map[self.top_song]
        self._save_top_song()
        return self.top_song

    def set_params(self):
        """
        パラメータの設定
        """
        self.k = 1
        self._create_k_bound_songs()

    def _create_k_bound_songs(self):
        """
        フィードバックの印象ベクトルの上位k個の学習データ作成
        """
        self._get_last_song()
        self._get_last_feedback()
        self._transform_feedback()
        self._get_bound_songs()

    def _get_last_song(self):
        """
        最後にフィードバックを受けた楽曲のidと印象ベクトル取得
        """
        self.top_song = common.get_scalar(self.r, "top_song", self.user)
        self.top_matrix = common.get_one_dim_params(self.r, "top_matrix_"+self.user)

    def _get_last_feedback(self):
        """
        最後のフィードバック情報取得
        """
        emotion_datas = models.EmotionEmotionbasedSong.objects.order_by("id").filter(user_id=int(self.user)).values()
        emotion_datas = emotion_datas.reverse()
        self.feedback = emotion_datas[0]["feedback_type"]

    def _transform_feedback(self):
        """
        feedback(1~6)を印象のベクトルに変換
        """
        if(self.feedback <= 2):
            self.plus_or_minus = 1
        else:
            self.plus_or_minus = -1
            self.feedback -= 3
        self.feedback += 1

    def _get_bound_songs(self):
        """
        フィードバックを受けた楽曲よりもemotionの値が高い楽曲s曲に対してranking学習を行う
        とりあえずその楽曲よりも直近で大きいs曲取得
        """
        top_song_objs = models.SearchMusicCluster.objects.filter(song_id=int(self.top_song)).values()
        emotion_value = top_song_objs[0][emotion_map[self.feedback]]
        self.bound_songs, self.bound_song_tag_map = common.get_bound_song_tag_map(emotion_value, self.k, self.plus_or_minus)

class EmotionFeedback(EmotionBaseline):
    """
    印象語フィードバックによるオンライン学習クラス
    """
    def __init__(self, user, emotions, situation):
        EmotionBaseline.__init__(self, user, emotions)
        self._get_params_by_redis()
        self.cy_obj = cy_ef.CyEmotionFeedback(self.W)
        self._set_emotion_dict()
        self.situation = situation

    def _get_params_by_redis(self):
        """
        redisからデータ取得
        """
        self.r = common.get_redis_obj(HOST, PORT, DB)
        key = "W_" + self.user
        self.W = common.get_one_dim_params(self.r, key)
 
    def set_params(self):
        """
        学習用データ作成
        """
        self._create_feedback_matrix()
    
    def set_params_k_rankings(self, k = 10):
        """
        フィードバックの印象ベクトルの上位k個の楽曲を学習するバージョン
        """
        self.k = k
        self._create_k_bound_songs()
    
    def fit(self):
        """
        学習
        """
        print "学習開始"
        X = self.feedback_matrix - self.top_matrix
        self.cy_obj.fit(X)
        self._update_params_into_redis()

    def k_online_fit(self):
        """
        上位k個のランキング学習
        上位K個の決定手法として、範囲アルファ*減衰定数の範囲で取得する
        オンライン学習
        """
        for song, tags in self.bound_song_tag_map.items():
            X = tags - self.top_matrix
            self.cy_obj.fit(X, True)
        self._update_params_into_redis()

    def k_batch_fit(self):
        """
        上位k個のランキング学習
        上位K個の決定手法として、範囲アルファ*減衰定数の範囲で取得する
        バッチ学習
        """
        self.W = self.cy_obj.PARank_fit(self.bound_song_tag_map, self.top_matrix, 0.005)
        print self.W
        self._update_params_into_redis()

    def get_top_k_songs(self, k=1):
        """
        検索対象の印象語に含まれている楽曲から回帰値の高いk個の楽曲を取得する
        """
        if hasattr(self, "feedback"):
            song_map = common.get_song_and_cluster()
            songs, song_tag_map = common.get_not_listening_songs(self.user, self.emotion_map, self.emotions, "emotion")
            rankings = [(self.cy_obj.predict(tags), song_id) for song_id, tags in song_tag_map.items()]
            common.listtuple_sort_reverse(rankings)
            self.top_song = rankings[0][1]
            common.write_top_k_songs(self.user, "emotion_k_song.txt", rankings[:10], self.emotion_map, self.emotions, emotion_map[self.feedback], self.plus_or_minus)
            self._save_top_k_songs(rankings[:5])
        else:
            songs, song_tag_map = common.get_initial_not_listening_songs(self.user, self.emotion_map, self.emotions, "emotion")
            random_song = random.randint(0,1000)
            self.top_song = songs[random_song]
            rankings = [(song_tag_map[self.top_song] ,self.top_song)]
            common.write_top_k_songs(self.user, "emotion_k_song.txt", rankings, self.emotion_map, self.emotions)
        self.top_matrix = song_tag_map[self.top_song]
        self._save_top_song()
        song_tags = []

        if hasattr(self, "feedback"):
            return rankings[:k]
        else:
            return rankings

    def _create_feedback_matrix(self):
        """
        特定のユーザーによるフィードバックを反映させた楽曲の特徴ベクトル生成
        top_matrix: 推薦された楽曲配列
        feedback_matrix: フィードバックを受けたタグの部分だけ値を大きくしたもの
        """
        self._get_last_song()
        self._get_last_feedback()
        self._get_tags_by_feedback()
        self.feedback_matrix = self.top_matrix.copy()
        alpha = 0.1 if self.plus_or_minus == 1 else -0.1 # フィードバックによって+-を分ける
        for tag in enumerate(self.tags):
            self.feedback_matrix[tag[0]] += alpha/self.feedback_matrix[tag[0]]

    def _get_tags_by_feedback(self):
        self._transform_feedback()
        tags = models.Tag.objects.filter(cluster__id=self.feedback+1)
        self.tags = [(tag.id-1, tag.name) for tag in tags]
    
    def _update_params_into_redis(self):
        """
        パラメータの更新
        """
        print "パラメータの更新"
        common.update_redis_key(self.r, "W_" + self.user, self.W)

    def _get_bound_songs(self):
        """
        _get_bound_songsをオーバーライド
        その印象に関するフィードバックの回数を取得して減衰定数を決定する
        減衰定数と境界パラメータを用いてkを動的に決定する
        他の値についても近いものを選ぶ
        """
        top_song_objs = models.SearchMusicCluster.objects.filter(song_id=int(self.top_song))
        top_song_obj = top_song_objs[0]
        emotion_value = top_song_objs[0].__dict__[emotion_map[self.feedback]]
        self._decision_bound(emotion_value)
        print "plus or minus %d" % (self.plus_or_minus)
        print "feedback %s" % (emotion_map[self.feedback])
        self.bound_songs, self.bound_song_tag_map = common.get_bound_with_attenuation_song_tag_map(self.feedback, top_song_obj, self.emotion_map, self.emotions, emotion_value, self.plus_or_minus, self.bound)
        print "number of bound songs %d" % (len(self.bound_songs))

    def _decision_bound(self, emotion_value):
        """
        boundの決定
        moreの時は最大値に近ければ近いほど、boundは小さくなる
        lessの時は最小値に近ければ近いほど、boundは小さくなる
        """
        # situationごとのフィードバックの回数を取得
        user_feedbacks = models.EmotionEmotionbasedSong.objects.filter(user_id=int(self.user), situation=int(self.situation)).values()
        diff = 0
        if self.plus_or_minus == 1:
            max_value = max_map[self.feedback]
            diff = max_value - emotion_value
            bound = bound_map[self.feedback] * diff / max_value
        else:
            min_value = min_map[self.feedback]
            diff = emotion_value - min_value
            bound = bound_map[self.feedback] * diff / emotion_value
        count = len(user_feedbacks)
        self.bound = bound / pow(2, count-1)
        print "bound %.5f" % (self.bound)
        #self.bound = bound_map[self.feedback] / count
        #self.bound = bound_map[self.feedback] * math.exp(-(count-1))

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
        common.delete_redis_key(self.r, key)
        for ranking in rankings:
            song_id = ranking[1]
            self.r.rpush(key, song_id)
