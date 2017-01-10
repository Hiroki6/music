# -*- coding:utf-8 -*-

"""
ランダムに楽曲を推薦するベースラインモデル
"""

import common_functions as common
import random
from recommendation import models

emotion_map = {1: "pop", 2: "ballad", 3: "rock"}

class InitSearch:
    def __init__(self, user, situation, emotions):
        self.user = user
        self.situation = situation
        self.emotions = map(int, emotions)
        self._set_emotion_dict()
    
    def get_top_k_songs(self):
        songs, song_tag_map = common.get_initial_not_listening_songs(self.user, self.emotion_map, self.emotions, "relevant")
        rankings = []
        random_index = []
        for i in xrange(100):
            random_song = random.randint(0,1000)
            if random_song not in random_index:
                random_index.append(random_song)
                song = songs[random_song]
                rankings.append((song_tag_map[song], song))
            if len(rankings) == 5:
                break

        return rankings

    def _set_emotion_dict(self):
        self.emotion_map = {}
        tags = models.Tag.objects.all()
        for tag in tags:
            if tag.search_flag:
                self.emotion_map[tag.id] = tag.name

