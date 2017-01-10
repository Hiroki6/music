# -*- coding:utf-8 -*-

import redis
import numpy as np
from recommendation import models
import codecs
import math
from Calculation import cy_calculation as cy_calc

cluster_map = {1: "pop", 2: "ballad", 3: "rock"}

# 距離の境界
bound_ave = 1.022828

top_k = 100

def get_scalar(redis_obj, key, field):
    """
    redisからのスカラー値の取得
    """
    return float(redis_obj.hget(key, field))

def get_one_dim_params(redis_obj, key):
    """
    redisから一次元配列の取得
    """
    params = redis_obj.lrange(key, 0, -1)
    params = np.array(params, dtype=np.float64)
    return params

def get_two_dim_by_redis(redis_obj, pre_key, n, m):
    """
    redisから二次元配列の取得
    """
    V = np.ones((m, n))
    for i in xrange(self.K):
        key = pre_key + str(i)
        v = redis_obj.lrange(key, 0, -1)
        V[i] = v
    V = np.array(V, dtype=np.float64)
    return V.T.copy(order='C')

def save_scalar(redis_obj, key, field, value):
    """
    スカラー値の保存
    """
    redis_obj.hset(key, field, value)

def save_one_dim_array(redis_obj, key, params):
    """
    redisへの一次元配列の保存
    """
    for param in params:
        redis_obj.rpush(key, param)

def save_two_dim_array(redis_obj, pre_key, params):
    """
    redisへの二次元配列の保存
    """
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


def get_not_listening_songs(user, emotion_map, emotions, feedback_type = "relevant"):
    """
    未視聴の楽曲を取得
    初期検索以降の際に使用
    """
    print "未視聴の楽曲取得"
    listening_songs = get_listening_songs_by_feedback_type(user, feedback_type)
    cluster_songs = models.SearchMusicCluster.objects.exclude(song_id__in=listening_songs).values("song")
    results = get_song_obj_by_cluster_songs(cluster_songs, emotion_map, emotions)
    return get_song_and_tag_map(results)

def get_initial_not_listening_songs(user, emotion_map, emotions, feedback_type):
    """
    未視聴の楽曲を取得
    初期検索時に使用
    """
    print "未視聴の楽曲取得"
    listening_songs = get_listening_songs_by_feedback_type(user, feedback_type)
    song_objs = get_extra_songs(listening_songs, emotion_map, emotions)
    return get_song_and_tag_map(song_objs)

def get_extra_songs(listening_songs, emotion_map, emotions):
    """
    複数のemotionの値の和が大きい1000曲を取得
    """
    # 複数のemotionsを足したextra_column
    extra_column = get_extra_column(emotion_map, emotions)
    # extra_column = ""
    # for index, emotion in enumerate(emotions):
    #     extra_column += emotion_map[emotion]
    #     if index != len(emotions) - 1:
    #         extra_column += "+"
    extra_results = models.Song.objects.extra(select = {'value': extra_column})
    song_objs = extra_results.exclude(id__in=listening_songs).extra(order_by=['-value']).values()[:1000]

    return song_objs

def get_extra_column(emotion_map, emotions):
    """
    検索条件に関連するカラムを取得する
    """
    extra_column = "("
    for index, emotion in enumerate(emotions):
        extra_column += emotion_map[emotion]
        if index != len(emotions) - 1:
            extra_column += "+"
        else:
            extra_column += ")/" + str(len(emotions))
    
    return extra_column

"""
def get_not_listening_songs(user, emotion, feedback_type = "relevant"):
    未視聴の楽曲取得
    print "未視聴の楽曲取得"
    listening_songs = get_listening_songs_by_feedback_type(user, feedback_type)
    cluster_songs = get_exclude_cluster_songs(listening_songs, int(emotion))
    results = get_song_obj_by_cluster_songs(cluster_songs)
    return get_song_and_tag_map(results)
"""

def get_song_obj_by_cluster_songs(cluster_songs, emotion_map, emotions):
    """
    MusicClusterオブジェクトからSongオブジェクトを取得する
    """
    top_k_songs = []
    results = []
    extra_column = get_extra_column(emotion_map, emotions)
    for song in cluster_songs:
        top_k_songs.append(song["song"])
    
    results = models.Song.objects.filter(id__in=top_k_songs).extra(select = {'value': extra_column}).values()

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

def get_listening_songs(user, emotion_map, emotions):
    """
    視聴済みの楽曲取得
    """
    listening_songs = models.EmotionRelevantSong.objects.filter(user=user).values('song')
    extra_column = get_extra_column(emotion_map, emotions)
    results = models.Song.objects.filter(id__in=listening_songs).extra(select = {'value': extra_column}).values()
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
        # クエリに関する特徴量を追加
        song_tag_map[song_id].append(song_obj["value"])

    change_list_into_numpy(song_tag_map)
    return songs, song_tag_map

def get_tags():
    """
    @return(tags): [tag_name]
    """
    tag_obj = models.Tag.objects.all()
    tags = [tag.name for tag in tag_obj]
    return tags

def get_tags_exclude_cluster(cluster):
    """
    clusterに所属しないタグのみ取得
    """
    tag_obj = models.SearchTag.objects.exclude(cluster=cluster_map[cluster])
    tags = [tag.name for tag in tag_obj]
    return tags

def get_song_and_cluster():
    songs = models.Song.objects.all().values()
    song_map = {}
    for song in songs:
        song_map[song["id"]] = song
    return song_map

def get_upper_songs(feedback_cluster, value, bound):
    """
    特定の印象ベクトルが特定の値より大きいものを取得
    """
    print "feedback is plus"
    if feedback_cluster == 1:
        return models.SearchMusicCluster.objects.order_by("pop").filter(pop__gte=value, pop__lte=value+bound)
    elif feedback_cluster == 2:
        return models.SearchMusicCluster.objects.order_by("ballad").filter(ballad__gte=value, ballad__lte=value+bound)
    else:
        return models.SearchMusicCluster.objects.order_by("rock").filter(rock__gte=value, rock__lte=value+bound)

def get_lower_songs(feedback_cluster, value, bound):
    print "feedback is minus"
    if feedback_cluster == 1:
        return models.SearchMusicCluster.objects.order_by("pop").filter(pop__lte=value, pop__gte=value-bound)
    elif feedback_cluster == 2:
        return models.SearchMusicCluster.objects.order_by("ballad").filter(ballad__lte=value, ballad__gte=value-bound)
    else:
        return models.SearchMusicCluster.objects.order_by("rock").filter(rock__lte=value, rock__gte=value-bound)

def get_bound_song_tag_map(feedback_cluster, value, k, plus_or_minus):

    songs = get_bound_songs(feedback_cluster, value, plus_or_minus)
    song_ids = []
    for song in songs[:k]:
        song_ids.append(song.song_id)

    song_objs = models.Song.objects.filter(id__in=song_ids).values()
    return get_song_and_tag_map(song_objs)

def get_bound_with_attenuation_song_tag_map(feedback_cluster, top_song_obj, emotion_map, emotions, value, plus_or_minus, bound):
    """
    @params(feedback_cluster): 印象タグ
    @params(top_song_obj): 対象楽曲のmusic cluster object
    @params(value): 対象楽曲の印象ベクトルの値
    @params(plus_or_minus): 上界か下界か
    @params(bound): 境界の値
    @returns(bound_songs): song_id配列
    @returns(bound_tag_map): song_idとtagの辞書(song_id: tags[])
    対象楽曲のクラスタの値も必要
    """
    m_objs, songs = get_bound_songs(feedback_cluster, value, bound, plus_or_minus)
    count = 0
    print "top_song feedback_cluster value: %.5f" % (value)
    top_song = get_song_by_musiccluster(top_song_obj)
    print len(songs)
    song_ids = []
    degree = len(songs[0])
    """
    feedback_clusterに所属するタグ以外のタグ間の距離を比較する
    全てのタグを比較してしまうと、feedback_clusterに該当する値の離れた楽曲が外れてしまうため
    """
    distances = [(cy_calc.get_euclid_distance(song, top_song, degree), m_obj.song_id) for m_obj, song in zip(m_objs, songs)]
    """for m_obj, song in zip(m_objs, songs):
        # 距離を計測する(ユークリッド距離)
        distance = cy_calc.get_euclid_distance(song, top_song, degree)
        print distance
        if distance > bound_ave:
            continue
        song_ids.append(m_obj.song_id)
        count += 1"""
    distances.sort()
    for i, distance in enumerate(distances):
        if i == 100:
            break
        song_ids.append(distance[1])
    extra_column = get_extra_column(emotion_map, emotions)
    song_objs = models.Song.objects.filter(id__in=song_ids).extra(select = {'value': extra_column}).values()
    #song_objs = s.extra(order_by=["-value"]).values()[:top_k]
    return get_song_and_tag_map(song_objs)

def is_upper_bound(song_obj, emotion, value, bound):
    """
    対象楽曲の特定のクラスタ値とvalueの差が境界(bound)を超えているかどうか
    """
    if emotion == 1:
        diff = abs(song_obj.pop - value)
        return diff > bound
    elif emotion == 2:
        diff = abs(song_obj.ballad - value)
        return diff > bound
    else:
        diff = abs(song_obj.rock - value)
        return diff > bound

def get_bound_songs(feedback_cluster, value, bound, plus_or_minus):
    """
    feedback_clusterカラムに対応する値がvalueよりも+or-方向に満たす楽曲を取得
    @returns(m_objs): SearchMusicClusterオブジェクト
    @returns(songs): Songオブジェクト
    """
    if plus_or_minus == 1:
        m_objs = get_upper_songs(feedback_cluster, value, bound)
    else:
        m_objs = get_lower_songs(feedback_cluster, value, bound)
        m_objs = m_objs.reverse()
    
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

def change_list_into_numpy(target_map):
    """
    listを持つdictをnumpy.arrayに変換
    """
    for key, values in target_map.items():
        target_map[key] = np.array(values)

def listtuple_sort_reverse(t):
    """
    タプルを要素として持つリストのソートして逆順にする
    """
    t.sort()
    t.reverse()

def write_top_k_songs(user_id, filepass, top_k_songs, emotion_map, emotions, feedback_type = "", plus_or_minus = 0):
    """
    上位k個の楽曲のファイルへの書き込み
    """
    print "write file"
    print emotions
    user_id = str(user_id).encode('utf-8')
    filepass = user_id + "_" + filepass
    f = codecs.open("file/" + filepass, "a")
    feedback_type = feedback_type.encode('utf-8')
    emotion = emotion_map[emotions[0]].encode('utf-8')
    if plus_or_minus == 1:
        f.write("user: " + user_id + " feedback_type: ↑" + feedback_type + " emotion: " + emotion + "\n")
    elif plus_or_minus == -1:
        f.write("user: " + user_id + " feedback_type: ↓" + feedback_type + " emotion: " + emotion + "\n")
    else:
        f.write("user: " + user_id + " feedback_type: " + feedback_type + " emotion: " + emotion + "\n")
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
