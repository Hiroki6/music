# -*- coding:utf-8 -*-

import redis
import numpy as np
from recommendation import models
import codecs

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

def delete_redis_keys(redis_obj, keys):

    for key in keys:
        delete_redis_key(redis_obj, key)

def delete_redis_key(redis_obj, key):
    redis_obj.delete(key)

def update_redis_key(redis_obj, key, params):

    delete_redis_key(redis_obj, key)
    save_one_dim_array(redis_obj, key, params)


"""
未視聴の楽曲取得
"""
def get_not_listening_songs(user, emotion, feedback_type = "relevant"):
    print "未視聴の楽曲取得"
    listening_songs = []
    if feedback_type == "relevant":
        listening_songs = get_listening_songs_by_relevant(user)
    else:
        listening_songs = get_listening_songs_by_emotion(user)
    cluster_songs = get_exclude_cluster_songs(listening_songs, int(emotion))
    """
    その印象クラスタが最も高い楽曲
    """
    #cluster_songs = models.MusicCluster.objects.exclude(song_id__in=listening_songs).filter(cluster_id=emotion).values('song')
    top_k_songs = []
    for song in cluster_songs:
        top_k_songs.append(song["song"])

    results = models.Song.objects.filter(id__in=top_k_songs).values()
    return get_song_and_tag_map(results)

def get_listening_songs_by_emotion(user):

    listening_songs = models.EmotionEmotionbasedSong.objects.filter(user=user).values('song')
    return listening_songs

def get_listening_songs_by_relevant(user):

    listening_songs = models.EmotionRelevantSong.objects.filter(user=user).values('song')
    return listening_songs

def get_exclude_cluster_songs(listening_songs, emotion):
    """
    上位1000曲
    """
    emotion_map = {1: "-calm", 2: "-tense", 3: "-aggressive", 4: "-lively", 5: "-peaceful"}
    cluster_songs = models.MusicCluster.objects.exclude(song_id__in=listening_songs).order_by(emotion_map[emotion]).values('song')[:1000]

    return cluster_songs


"""
視聴済みの楽曲取得
"""
def get_listening_songs(user):

    listening_songs = models.EmotionRelevantSong.objects.filter(user=user).values('song')
    results = models.Song.objects.filter(id__in=listening_songs).values()
    return get_song_and_tag_map(results)

def get_song_and_tag_map(song_objs):

    tag_obj = models.Tag.objects.all()
    tags = [tag.name for tag in tag_obj]

    song_tag_map = {} # {song_id: List[tag_value]}
    songs = [] # List[song_id]
    for song_obj in song_objs:
        song_id = song_obj['id']
        songs.append(song_id)
        song_tag_map.setdefault(song_id, [])
        for tag in tags:
            song_tag_map[song_id].append(song_obj[tag])
    
    change_list_into_numpy(song_tag_map)
    return songs, song_tag_map

"""
特定の印象ベクトルが特定の値より大きいものを取得
"""
def get_upper_songs(emotion, value):

    if emotion == 0:
        return models.MusicCluster.objects.order_by("calm").filter(calm__gte=value).values()
    elif emotion == 1:
        return models.MusicCluster.objects.order_by("tense").filter(tense__gte=value).values()
    elif emotion == 2:
        return models.MusicCluster.objects.order_by("aggressive").filter(aggressive__gte=value).values()
    elif emotion == 3:
        return models.MusicCluster.objects.order_by("lively").filter(lively__gte=value).values()
    else:
        return models.MusicCluster.objects.order_by("peaceful").filter(peaceful__gte=value).values()

def get_lower_songs(emotion, value):

    if emotion == 0:
        return models.MusicCluster.objects.order_by("calm").filter(calm__lte=value).values()
    elif emotion == 1:
        return models.MusicCluster.objects.order_by("tense").filter(tense__lte=value).values()
    elif emotion == 2:
        return models.MusicCluster.objects.order_by("aggressive").filter(aggressive__lte=value).values()
    elif emotion == 3:
        return models.MusicCluster.objects.order_by("lively").filter(lively__lte=value).values()
    else:
        return models.MusicCluster.objects.order_by("peaceful").filter(peaceful__lte=value).values()

def get_bound_song_tag_map(emotion, value, k, plus_or_minus):

    if plus_or_minus == 1:
        songs = get_upper_songs(emotion, value)
        songs = songs.reverse()
    else:
        songs = get_lower_songs(emotin, value)
    song_ids = []
    for song in songs[:k]:
        song_ids.append(song["song_id"])

    song_objs = models.Song.objects.filter(id__in=song_ids).values()
    return get_song_and_tag_map(song_objs)

"""
listを持つdictをnumpy.arrayに変換
"""
def change_list_into_numpy(target_map):

    for key, values in target_map.items():
        target_map[key] = np.array(values)

def listtuple_sort_reverse(t):
    t.sort()
    t.reverse()

def write_top_k_songs(user_id, filepass, top_k_songs):
    """
    上位k個の楽曲のファイルへの書き込み
    """

    print "write file"
    f = codecs.open(filepass, "a")
    f.write("user: " + str(user_id) + "\n")
    for song in top_k_songs:
        content = str(song) + "\n"
        f.write(content)
    f.write("\n")
    f.close()
