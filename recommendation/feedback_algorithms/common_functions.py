# -*- coding:utf-8 -*-

import redis
import numpy as np
from recommendation import models
import codecs
import math
from Calculation import cy_calculation as cy_calc

emotion_map = {1: "pop", 2: "ballad", 3: "rock"}

cluster_map = {1: "pop", 2: "ballad", 3: "rock"}

bound_ave = 1.022828

top_k = 100

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


def get_not_listening_songs_by_multi_emotion(user, emotions, feedback_type = "relevant", is_first = False):
    print "未視聴の楽曲取得"
    listening_songs = get_listening_songs_by_feedback_type(user, feedback_type)
    cluster_songs = extra_cluster_songs(listening_songs, emotions, is_first)
    results = get_song_obj_by_cluster_songs(cluster_songs)
    return get_song_and_tag_map(results)

def extra_cluster_songs(listening_songs, emotions, is_first = False):
    # 複数のemotionsを足したextra_column
    extra_column = ""
    # for emotion in emotions:
    #     extra_column += emotion_map[int(emotion)] + "+"
    extra_column += emotion_map[int(emotions[0])]
    #extra_column = extra_column[:-1]
    extra_results = models.SearchMusicCluster.objects.extra(select = {'value': extra_column})
    if is_first:
        cluster_songs = extra_results.exclude(song_id__in=listening_songs).extra(order_by=['-value']).values("song")[:1000]
    else:
        cluster_songs = extra_results.exclude(song_id__in=listening_songs).extra(order_by=['-value']).values("song")

    return cluster_songs

"""
未視聴の楽曲取得
"""
def get_not_listening_songs(user, emotion, feedback_type = "relevant"):
    print "未視聴の楽曲取得"
    listening_songs = get_listening_songs_by_feedback_type(user, feedback_type)
    cluster_songs = get_exclude_cluster_songs(listening_songs, int(emotion))
    results = get_song_obj_by_cluster_songs(cluster_songs)
    return get_song_and_tag_map(results)

def get_song_obj_by_cluster_songs(cluster_songs):
    top_k_songs = []
    for song in cluster_songs:
        top_k_songs.append(song["song"])
    
    results = models.Song.objects.filter(id__in=top_k_songs).values()

    return results

def get_listening_songs_by_feedback_type(user, feedback_type):
    if feedback_type == "relevant":
        return get_listening_songs_by_relevant(user)
    else:
        return get_listening_songs_by_emotion(user)

def get_listening_songs_by_emotion(user):

    listening_songs = models.EmotionEmotionbasedSong.objects.filter(user=user).values('song')
    return listening_songs

def get_listening_songs_by_relevant(user):

    listening_songs = models.EmotionRelevantSong.objects.filter(user=user).values('song')
    return listening_songs

def get_exclude_cluster_songs(listening_songs, emotion):
    emotion_order_map = {1: "-pop", 2: "-ballad", 3: "-rock"}
    cluster_songs = models.SearchMusicCluster.objects.exclude(song_id__in=listening_songs).order_by(emotion_order_map[emotion]).values('song')

    return cluster_songs

"""
視聴済みの楽曲取得
"""
def get_listening_songs(user):

    listening_songs = models.EmotionRelevantSong.objects.filter(user=user).values('song')
    results = models.Song.objects.filter(id__in=listening_songs).values()
    return get_song_and_tag_map(results)

def get_song_and_tag_map(song_objs):

    tags = get_tags()
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
@return(tags): [tag_name]
"""
def get_tags():

    tag_obj = models.Tag.objects.all()
    tags = [tag.name for tag in tag_obj]
    return tags

def get_song_and_cluster():

    songs = models.SearchMusicCluster.objects.all().values()
    song_cluster_map = {}
    for song in songs:
        song_cluster_map[song["song_id"]] = song
    return song_cluster_map
"""
特定の印象ベクトルが特定の値より大きいものを取得
"""
def get_upper_songs(emotion, value, bound):

    if emotion == 1:
        print "pop"
        return models.SearchMusicCluster.objects.order_by("pop").filter(pop__gte=value, pop__lte=value+bound)
    elif emotion == 2:
        print "ballad"
        return models.SearchMusicCluster.objects.order_by("ballad").filter(ballad__gte=value, ballad__lte=value+bound)
    else:
        print "rock"
        return models.SearchMusicCluster.objects.order_by("rock").filter(rock__gte=value, rock__lte=value+bound)

def get_lower_songs(emotion, value, bound):

    if emotion == 1:
        print "pop"
        return models.SearchMusicCluster.objects.order_by("pop").filter(pop__lte=value, pop__gte=value-bound)
    elif emotion == 2:
        print "ballad"
        return models.SearchMusicCluster.objects.order_by("ballad").filter(ballad__lte=value, ballad__gte=value-bound)
    else:
        print "rock"
        return models.SearchMusicCluster.objects.order_by("rock").filter(rock__lte=value, rock__gte=value-bound)

def get_bound_song_tag_map(emotion, value, k, plus_or_minus):

    songs = get_bound_songs(emotion, value, plus_or_minus)
    song_ids = []
    for song in songs[:k]:
        song_ids.append(song.song_id)

    song_objs = models.Song.objects.filter(id__in=song_ids).values()
    return get_song_and_tag_map(song_objs)

"""
@params(emotion): 印象タグ
@params(top_song_obj): 対象楽曲のmusic cluster object
@params(value): 対象楽曲の印象ベクトルの値
@params(plus_or_minus): 上界か下界か
@params(bound): 境界の値
対象楽曲のクラスタの値も必要
"""
def get_bound_with_attenuation_song_tag_map(feedback_cluster, top_song_obj, value, plus_or_minus, bound):

    m_objs, songs = get_bound_songs(feedback_cluster, value, bound, plus_or_minus)
    tags = get_tags()
    song_ids = []
    count = 0
    print "top_song emotion value: %.5f" % (value)
    top_song = get_song_by_musiccluster(top_song_obj)
    print len(songs)
    song_ids = []
    degree = len(songs[0])
    #for m_obj, song in zip(m_objs, songs):
        # distance = cy_calc.get_euclid_distance(song, top_song, degree)
        # if distance > bound_ave:
        #     continue
        # song_ids.append(m_obj.song_id)
        # count += 1
    if plus_or_minus == 1:
        distances = [(m_obj.__dict__[cluster_map[feedback_cluster]] / cy_calc.get_euclid_distance(song, top_song, degree), m_obj.song_id) for m_obj, song in zip(m_objs, songs)]
        distances.sort()
        distances.reverse()
    else:
        distances = [(m_obj.__dict__[cluster_map[feedback_cluster]] * cy_calc.get_euclid_distance(song, top_song, degree), m_obj.song_id) for m_obj, song in zip(m_objs, songs)]
        distances.sort()
    # count = 0
    # max_value = sum([d[0] for d in distances])
    # for i in xrange(100):
    #     song_id = select_train_song(max_value, distances)
    #     if song_id not in song_ids:
    #         song_ids.append(song_id)
    #         count += 1
    #     if count == 10:
    #         break
    for i, distance in enumerate(distances):
        if i == top_k:
            break
        song_ids.append(distance[1])
    song_objs = models.Song.objects.filter(id__in=song_ids).values()
    return get_song_and_tag_map(song_objs)

def is_upper_bound(song_obj, emotion, value, bound):

    if emotion == 1:
        diff = abs(song_obj.pop - value)
        # print "diff: %.5f" % (diff)
        return diff > bound
    elif emotion == 2:
        diff = abs(song_obj.ballad - value)
        # print "diff: %.5f" % (diff)
        return diff > bound
    else:
        diff = abs(song_obj.rock - value)
        # print "diff: %.5f" % (diff)
        return diff > bound

def get_bound_songs(feedback_cluster, value, bound, plus_or_minus):

    if plus_or_minus == 1:
        m_objs = get_upper_songs(feedback_cluster, value, bound)
        #songs = songs.reverse()
    else:
        m_objs = get_lower_songs(feedback_cluster, value, bound)
        m_objs = songs.reverse()

    songs = get_songs_by_musicclusters(feedback_cluster, m_objs)
    return m_objs, songs

def get_songs_by_musicclusters(feedback_cluster, m_objs):
    """
    SearchMusicClusterからsong_tags配列取得
    """
    tags = get_tags_exclude_cluster(feedback_cluster)
    songs = np.zeros((len(m_objs), len(tags)))
    for m_index, m_obj in enumerate(m_objs):
        song_obj = m_obj.song.__dict__
        for index, tag in enumerate(tags):
            songs[m_index][index] = song_obj[tag]

    return songs

def get_tags_exclude_cluster(cluster):
    """
    clusterに所属しないタグのみ取得
    """
    tag_obj = models.SearchTag.objects.exclude(cluster=cluster_map[cluster])
    tags = [tag.name for tag in tag_obj]
    return tags

def get_song_by_musiccluster(m_obj):
    """
    SearchMusicClusterオブジェクトから{song: tags[]}取得
    """
    tags = get_tags()
    song = np.zeros(43)
    song_obj = m_obj.song.__dict__
    for index, tag in enumerate(tags):
        song[index] = song_obj[tag]

    return song

"""
listを持つdictをnumpy.arrayに変換
"""
def change_list_into_numpy(target_map):

    for key, values in target_map.items():
        target_map[key] = np.array(values)

def listtuple_sort_reverse(t):
    t.sort()
    t.reverse()

def write_top_k_songs(user_id, filepass, top_k_songs, emotions, feedback_type = "", plus_or_minus = 0):
    """
    上位k個の楽曲のファイルへの書き込み
    """

    print "write file"
    print emotions
    f = codecs.open(filepass, "a")
    if plus_or_minus == 1:
        f.write("user: " + str(user_id) + " feedback_type: ↑" + feedback_type + " emotion: " + emotion_map[int(emotions[0])] + "\n")
    elif plus_or_minus == -1:
        f.write("user: " + str(user_id) + " feedback_type: ↓" + feedback_type + " emotion: " + emotion_map[int(emotions[0])] + "\n")
    else:
        f.write("user: " + str(user_id) + " feedback_type: " + feedback_type + " emotion: " + emotion_map[int(emotions[0])] + "\n")
    f.write("predict_value, song_id, pop, ballad, rock\n")
    for song in top_k_songs:
        song_obj = get_music_cluster_value(song[1])
        content = str(song) + "," + str(song_obj["pop"]) + "," + str(song_obj["ballad"]) + "," + str(song_obj["rock"]) + "\n"
        f.write(content)
    f.write("\n")
    f.close()

def get_music_cluster_value(song_id):
    top_song_objs = models.SearchMusicCluster.objects.filter(song_id=int(song_id)).values()[0]
    return top_song_objs
