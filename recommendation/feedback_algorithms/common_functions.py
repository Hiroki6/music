# -*- coding:utf-8 -*-

import redis
import numpy as np
from recommendation import models

"""
redisからのスカラー値の取得
"""
def get_scalar(redis_obj, key, field):
    return float(redis_obj.hget(key, field))

"""
redisから一次元配列の取得
"""
def get_one_dim_params(redis_obj, key):

    params = redis_obj.lrange(key, 0, -1)
    params = np.array(params, dtype=np.float64)
    return params

"""
redisから二次元配列の取得
"""
def get_two_dim_by_redis(redis_obj, pre_key, n, m):

    V = np.ones((m, n))
    for i in xrange(self.K):
        key = pre_key + str(i)
        v = redis_obj.lrange(key, 0, -1)
        V[i] = v
    V = np.array(V, dtype=np.float64)
    return V.T.copy(order='C')

"""
スカラー値の保存
"""
def save_scalar(redis_obj, key, field, value):

    redis_obj.hset(key, field, value)

"""
redisへの一次元配列の保存
"""
def save_one_dim_array(redis_obj, key, params):
   
    for param in params:
        redis_obj.rpush(key, param)

"""
redisへの二次元配列の保存
"""
def save_two_dim_array(redis_obj, pre_key, params):
   
    for i in xrange(len(params)):
        key = pre_key + str(i)
        for param in params[i]:
            redis_obj.rpush(key, param)

def get_redis_obj(host, port, db):
    return redis.Redis(host=host, port=port, db=db)

"""
フィードバックの種類によって視聴済みの楽曲を取得するモデルを変える必要がある
"""
def get_not_listening_songs(user, emotion):
    print "未視聴の楽曲取得"
    listening_songs = models.EmotionRelevantSong.objects.filter(user=user).values('song')
    emotion_map = {1: "-calm", 2: "-tense", 3: "-aggressive", 4: "-lively", 5: "-peaceful"}
    cluster_songs = models.MusicCluster.objects.exclude(song_id__in=listening_songs).order_by(emotion_map[emotion]).values('song')[:300]
    top_k_songs = []
    for song in cluster_songs:
        top_k_songs.append(song["song"])
    results = models.Song.objects.filter(id__in=top_k_songs).values()
    tag_obj = models.Tag.objects.all()
    tags = [tag.name for tag in tag_obj]

    song_tag_map = {} # {song_id: List[tag_value]}
    songs = [] # List[song_id]
    for result in results:
        song_id = result['id']
        songs.append(song_id)
        song_tag_map.setdefault(song_id, [])
        for tag in tags:
            song_tag_map[song_id].append(result[tag])

    return songs, song_tag_map
