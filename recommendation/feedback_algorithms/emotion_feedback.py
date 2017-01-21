# -*- coding:utf-8 -*-

"""
印象語検索における印象語フィードバックによるモデルの学習
"""

import numpy as np
import redis
import common_functions as common
import redis_functions as redis_f
from EmotionFeedback import cy_emotion_feedback as cy_ef
import sys
from recommendation import models
import math
import random

HOST = 'localhost'
PORT = 6379
DB = 3

emotion_map = {1: "pop", 2: "ballad", 3: "rock", 7: "no feedback"}

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
    cf_obj: 共通の関数を扱うクラス
    """
    def __init__(self, user, cf_obj):
        self.user = user
        self._get_last_feedback()
        self.plus_or_minus = 0
        self.cf_obj = cf_obj

    def _save_top_song(self):
        """
        top_songの保存
        """
        redis_f.delete_redis_key(self.r, "top_matrix_" + self.user)
        redis_f.save_scalar(self.r, "top_song", self.user, self.top_song)
        redis_f.save_one_dim_array(self.r, "top_matrix_"+self.user, self.top_matrix)

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
        self._transform_feedback()
        self._get_bound_songs()

    def _get_last_song(self):
        """
        最後にフィードバックを受けた楽曲のidと印象ベクトル取得
        """
        self.top_song = redis_f.get_scalar(self.r, "top_song", self.user)
        self.top_matrix = redis_f.get_one_dim_params(self.r, "top_matrix_"+self.user)

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
        self.bound_songs, self.bound_song_tag_map = self.cf_obj.get_bound_song_tag_map(emotion_value, self.k, self.plus_or_minus)

class EmotionFeedback(EmotionBaseline):
    """
    印象語フィードバックによるオンライン学習クラス
    """
    def __init__(self, user, situation, emotions, cf_obj):
        EmotionBaseline.__init__(self, user, cf_obj)
        self.emotions = map(int, emotions)
        self._get_params_by_redis()
        self.cy_obj = cy_ef.CyEmotionFeedback(self.W)
        self._set_emotion_dict()
        self.situation = situation

    def _get_params_by_redis(self):
        """
        redisからデータ取得
        """
        self.r = redis_f.get_redis_obj(HOST, PORT, DB)
        key = "W_" + self.user
        self.W = redis_f.get_one_dim_params(self.r, key)
 
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
        print self.W
        self.W = self.cy_obj.PARank_fit(self.bound_song_tag_map, self.top_matrix, 0.005)
        self._update_params_into_redis()

    def get_init_songs(self):
        songs = self.cf_obj.get_init_songs_by_redis("init_songs_" + str(self.user))
        return songs[:1]

    def get_top_k_songs(self, k=1):
        """
        検索対象の印象語に含まれている楽曲から回帰値の高いk個の楽曲を取得する
        """
        song_map = self.cf_obj.get_song_and_cluster()
        songs, song_tag_map = self.cf_obj.get_not_listening_songs(self.emotion_map, self.emotions, "emotion")
        rankings = [(self.cy_obj.predict(tags), song_id) for song_id, tags in song_tag_map.items()]
        self.cf_obj.listtuple_sort_reverse(rankings)
        self.top_song = rankings[0][1]
        self.cf_obj.write_top_k_songs_emotion("emotion_k_song.txt", rankings[:10], self.emotion_map, self.emotions, emotion_map[self.feedback], self.plus_or_minus)
        self._save_top_k_songs(rankings[:5])
        self.top_matrix = song_tag_map[self.top_song]
        self._save_top_song()
        song_tags = []

        return rankings[:k]

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
        redis_f.update_redis_key(self.r, "W_" + self.user, self.W)

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
        for i in xrange(10):
            self.bound_songs, self.bound_song_tag_map = self.cf_obj.get_bound_with_attenuation_song_tag_map(self.feedback, top_song_obj, self.emotion_map, self.emotions, emotion_value, self.plus_or_minus, self.bound)
            if len(self.bound_songs) >= 1:
                break
            self.bound *= 2
        print "number of bound songs %d" % (len(self.bound_songs))

    def _decision_bound(self, emotion_value):
        """
        boundの決定
        moreの時は最大値に近ければ近いほど、boundは小さくなる
        lessの時は最小値に近ければ近いほど、boundは小さくなる
        """
        # situationごとのフィードバックの回数を取得
        user_feedbacks = models.EmotionEmotionbasedSong.objects.filter(user_id=int(self.user), situation=int(self.situation)).exclude(feedback_type=7).values()
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
        print "feedback_count: %d" % count
        self.bound = bound / pow(2, count-1)
        #self.bound = bound_map[self.feedback] / count
        print "bound %.5f" % (self.bound)
        #self.bound = bound_map[self.feedback] * math.exp(-(count-1))

    def _set_emotion_dict(self):
        self.emotion_map = {}
        tags = models.Tag.objects.all()
        for tag in tags:
            if tag.search_flag:
                self.emotion_map[tag.id] = tag.name

    def _save_top_k_songs(self, rankings):
        """
        現在のtop_kの楽曲をredisに保存
        """
        key = "top_k_songs_" + self.user
        redis_f.delete_redis_key(self.r, key)
        for ranking in rankings:
            song_id = ranking[1]
            redis_f.rpush_redis_key(self.r, key, song_id)

    def _save_bound_song(self):
        """
        フィードバック対象の楽曲のidを持つkeyに学習用idを保存
        あまりにも速度が遅い場合はファイルに保存してもいいかもしれない
        """
        redis_f.save_one_dim_array(self.r, "train_data_" + str(self.top_song), self.bound_songs)

    def _get_train_songs(self):
        """
        今までの学習に用いたデータを取得
        """
        # train_datas: {song_id: [train_ids]}
        self.train_datas = {}
        feedback_songs = EmotionEmotionbasedSong.objects.filter(user_id=self.user_id, situation=self.situation)
        for feedback_song in feedback_songs:
            song_id = feedback_song.song_id
            self.train_datas[song_id] = self.cf_obj.get_one_dim_params_int(self.r, "train_data_" + str(self.song_id))

class EmotionFeedbackRandom(EmotionFeedback):
    """
    印象語フィードバックによるオンライン学習クラス
    状況のみの検索を行うため、emotionsは用いない
    """
    def __init__(self, user, situation, cf_obj):
        EmotionFeedback.__init__(self, user, situation, [], cf_obj)

    def get_top_k_songs(self, k=1):
        """
        検索対象の印象語に含まれている楽曲から回帰値の高いk個の楽曲を取得する
        """
        song_map = self.cf_obj.get_song_and_cluster()
        songs, song_tag_map = self.cf_obj.get_not_listening_songs("emotion")
        rankings = [(self.cy_obj.predict(tags), song_id) for song_id, tags in song_tag_map.items()]
        self.cf_obj.listtuple_sort_reverse(rankings)
        self.top_song = rankings[0][1]
        self.cf_obj.write_top_k_songs_emotion("random_emotion_k_song.txt", rankings[:10], {}, [], emotion_map[self.feedback], self.plus_or_minus)
        self._save_top_k_songs(rankings[:5])
        #self._save_top_k_songs_now_order(rankings[:5])
        self.top_matrix = song_tag_map[self.top_song]
        self._save_top_song()
        song_tags = []

        return rankings[:k]

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
        # 学習データが０だった場合は繰り返し
        for i in xrange(10):
            self.bound_songs, self.bound_song_tag_map = self.cf_obj.get_bound_with_attenuation_song_tag_map(self.feedback, top_song_obj, emotion_value, self.plus_or_minus, self.bound)
            if len(self.bound_songs) >= 1:
                break
            self.bound *= 2
        print "number of bound songs %d" % (len(self.bound_songs))

    def _save_top_k_songs_now_order(self, rankings):
        """
        現在の順番のインタラクションの時のtop_k_songsをredisに保存する
        """
        count = self.cf_obj.get_now_order(self.situation, 1)
        key = "top_k_songs_" + self.user + "_" + str(count)
        redis_f.delete_redis_key(self.r, key)
        for ranking in rankings:
            song_id = ranking[1]
            redis_f.rpush_redis_key(self.r, key, song_id)
