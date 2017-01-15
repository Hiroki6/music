# -*- coding:utf-8 -*-

"""
ランダムに楽曲を推薦するベースラインモデル
"""

import common_functions as common
import random
from recommendation import models

emotion_map = {1: "pop", 2: "ballad", 3: "rock"}

HOST = 'localhost'
PORT = 6379
INIT_DB = 1
EMOTION_DB = 3

class InitSearch:
    """
    初期検索の際のクラス
    """
    def __init__(self, user, situation, emotions):
        self.user = user
        self.situation = situation
        self.emotions = map(int, emotions)
        self._set_emotion_dict()
        self.r = common.get_redis_obj(HOST, PORT, INIT_DB)
        print self.emotions
    
    def get_top_k_songs(self):
        """
        上位１０００曲からランダムに５曲選択する
        """
        songs, song_tag_map = common.get_initial_not_listening_songs(self.user, self.emotion_map, self.emotions, "relevant")
        top_k_songs = []
        random_indexes = []
        for i in xrange(100):
            random_index = random.randint(0,1000)
            if random_index not in random_indexes:
                random_indexes.append(random_index)
                song = songs[random_index]
                top_k_songs.append(song)
            if len(top_k_songs) == 5:
                break
        # redisに保存
        common.update_redis_key(self.r, "init_songs_" + str(self.user), top_k_songs)
        self._save_top_matrixes(top_k_songs)
        # ファイルに書き込み
        common.write_top_k_songs_init(self.user, "init_song.txt", top_k_songs, self.emotion_map, self.emotions)
        return top_k_songs

    def _set_emotion_dict(self):
        """
        タグのidと名前の辞書
        """
        self.emotion_map = {}
        tags = models.Tag.objects.all()
        for tag in tags:
            if tag.search_flag:
                self.emotion_map[tag.id] = tag.name

    def _save_top_matrixes(self, top_k_songs):
        """
        印象語フィードバック用にtop_songとtop_matrix(44)を保存する
        """
        r = common.get_redis_obj(HOST, PORT, EMOTION_DB)
        common.save_scalar(r, "top_song", str(self.user), top_k_songs[0])
        self._get_top_matrix(top_k_songs[0])
        common.update_redis_key(r, "top_matrix_" + str(self.user), self.top_matrix)

    def _get_top_matrix(self, song_id):
        song_tag_map = common.get_song_tag_map_by_song_ids([song_id], self.emotion_map, self.emotions)
        self.top_matrix = song_tag_map[1][song_id]
