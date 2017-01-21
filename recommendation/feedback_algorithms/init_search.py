# -*- coding:utf-8 -*-

"""
ランダムに楽曲を推薦するベースラインモデル
"""

import common_functions as common
import redis_functions as redis_f
import random
from recommendation import models

emotion_map = {1: "pop", 2: "ballad", 3: "rock"}

HOST = 'localhost'
PORT = 6379
INIT_DB = 1
EMOTION_DB = 3

class InitSearch(object):
    """
    初期検索の際のクラス
    """
    def __init__(self, user, situation, emotions, cf_obj):
        self.user = user
        self.situation = situation
        self.emotions = map(int, emotions)
        self._set_emotion_dict()
        self.r = redis_f.get_redis_obj(HOST, PORT, INIT_DB)
        self.cf_obj = cf_obj

    def get_top_k_songs(self):
        """
        上位１０００曲からランダムに５曲選択する
        """
        songs, song_tag_map = self.cf_obj.get_initial_not_listening_songs(self.emotion_map, self.emotions, "relevant")
        top_k_songs = []
        #random_indexes = []
        max_value = sum([song_tag_map[song][43] for song in songs])
        count = 0
        for i in xrange(100):
            song = self.cf_obj.select_initial_song(max_value, songs, song_tag_map)
            if song not in top_k_songs:
                top_k_songs.append(song)
                count += 1
            if count == 5:
                break
        # redisに保存
        redis_f.update_redis_key(self.r, "init_songs_" + str(self.user), top_k_songs)
        self._save_top_matrixes(top_k_songs[0])
        # ファイルに書き込み
        self.cf_obj.write_top_k_songs_init("init_song.txt", top_k_songs, self.emotion_map, self.situation, self.emotions)
        return top_k_songs
    
    def get_next_song(self, listening_count):
        """
        redisから次の楽曲を取得する
        """
        next_song = int(self.cf_obj.get_next_elem_by_pop(self.r, "init_songs_" + str(self.user), listening_count))
        self._save_top_matrixes(next_song)
        # ファイルに書き込み
        self.cf_obj.write_top_k_songs_init("init_song.txt", [next_song], self.emotion_map, self.situation, self.emotions)
        return next_song

    def _set_emotion_dict(self):
        """
        タグのidと名前の辞書
        """
        self.emotion_map = {}
        tags = models.Tag.objects.all()
        for tag in tags:
            if tag.search_flag:
                self.emotion_map[tag.id] = tag.name

    def _save_top_matrixes(self, top_song):
        """
        印象語フィードバック用にtop_songとtop_matrix(44)を保存する
        """
        r = redis_f.get_redis_obj(HOST, PORT, EMOTION_DB)
        redis_f.save_scalar(r, "top_song", str(self.user), top_song)
        self._get_top_matrix(top_song)
        redis_f.update_redis_key(r, "top_matrix_" + str(self.user), self.top_matrix)

    def _get_top_matrix(self, song_id):
        song_tag_map = self.cf_obj.get_song_tag_map_by_song_ids([song_id], self.emotion_map, self.emotions)
        self.top_matrix = song_tag_map[1][song_id]


class InitRandomSearch(InitSearch):
    """
    初期検索の際のクラス
    検索条件なし
    """
    def __init__(self, user, situation, cf_obj):
        InitSearch.__init__(self, user, situation, [], cf_obj)

    def get_top_k_songs(self):
        """
        上位１０００曲からランダムに５曲選択する
        """
        songs, song_tag_map = self.cf_obj.get_initial_not_listening_songs(self.emotion_map, "relevant")
        top_k_songs = []
        #random_indexes = []
        count = 0
        for i in xrange(100):
            random_index = random.randint(0, len(songs))
            song = songs[random_index]
            if song not in top_k_songs:
                top_k_songs.append(song)
                count += 1
            if count == 5:
                break
        # redisに保存
        redis_f.update_redis_key(self.r, "init_songs_" + str(self.user), top_k_songs)
        self._save_top_matrixes(top_k_songs[0])
        # ファイルに書き込み
        self.cf_obj.write_top_k_songs_init("init_song.txt", top_k_songs, {}, self.situation, [])
        return top_k_songs
    
    def get_next_song(self, listening_count):
        """
        redisから次の楽曲を取得する
        """
        next_song = int(redis_f.get_next_elem_by_pop(self.r, "init_songs_" + str(self.user), listening_count))
        self._save_top_matrixes(next_song)
        # ファイルに書き込み
        self.cf_obj.write_top_k_songs_init("random_init_song.txt", [next_song], {}, self.situation, [])
        return next_song

    def _get_top_matrix(self, song_id):
        song_tag_map = self.cf_obj.get_song_tag_map_by_song_ids([song_id])
        self.top_matrix = song_tag_map[1][song_id]

