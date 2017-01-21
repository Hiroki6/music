# -*- coding:utf-8 -*-

import redis
import numpy as np
from recommendation import models
import codecs
import math
import random
from Calculation import cy_calculation as cy_calc

cluster_map = {1: "pop", 2: "ballad", 3: "rock"}

# 距離の境界
bound_ave = 1.022828

top_k = 10

class CommonFunctions(object):
    """
    共通の関数を集めたクラス
    """
    def __init__(self, user):
        self.user = int(user)

    def get_not_listening_songs(self, emotion_map, emotions, feedback_type = "relevant"):
        """
        未視聴の楽曲を取得
        初期検索以降の際に使用
        """
        print "未視聴の楽曲取得"
        listening_songs = self._get_listening_songs_by_feedback_type(feedback_type)
        cluster_songs = models.SearchMusicCluster.objects.exclude(song_id__in=listening_songs).values("song")
        results = self._get_song_obj_by_cluster_songs(cluster_songs, emotion_map, emotions)
        return self._get_song_and_tag_map(results)

    def get_initial_not_listening_songs(self, emotion_map, emotions, feedback_type):
        """
        未視聴の楽曲を取得
        初期検索時に使用
        """
        print "未視聴の楽曲取得"
        listening_songs = self._get_listening_songs_by_feedback_type(feedback_type)
        song_objs = self._get_extra_songs(listening_songs, emotion_map, emotions)
        return self._get_song_and_tag_map(song_objs)

    def _get_extra_songs(self, listening_songs, emotion_map, emotions):
        """
        複数のemotionの値の和が大きい1000曲を取得
        """
        # 複数のemotionsを足したextra_column
        extra_column = self._get_extra_column(emotion_map, emotions)
        # extra_column = ""
        # for index, emotion in enumerate(emotions):
        #     extra_column += emotion_map[emotion]
        #     if index != len(emotions) - 1:
        #         extra_column += "+"
        extra_results = models.Song.objects.extra(select = {'value': extra_column})
        song_objs = extra_results.exclude(id__in=listening_songs).extra(order_by=['-value']).values()[:1000]

        return song_objs

    def _get_extra_column(self, emotion_map, emotions):
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
        listening_songs = _get_listening_songs_by_feedback_type(user, feedback_type)
        cluster_songs = get_exclude_cluster_songs(listening_songs, int(emotion))
        results = _get_song_obj_by_cluster_songs(cluster_songs)
        return self._get_song_and_tag_map(results)
    """

    def _get_song_obj_by_cluster_songs(self, cluster_songs, emotion_map, emotions):
        """
        MusicClusterオブジェクトからSongオブジェクトを取得する
        """
        top_k_songs = []
        results = []
        extra_column = self._get_extra_column(emotion_map, emotions)
        for song in cluster_songs:
            top_k_songs.append(song["song"])
        
        results = models.Song.objects.filter(id__in=top_k_songs).extra(select = {'value': extra_column}).values()

        return results

    def _get_listening_songs_by_feedback_type(self, feedback_type):
        if feedback_type == "relevant":
            return self._get_listening_songs_by_relevant()
        else:
            return self._get_listening_songs_by_emotion()

    def _get_listening_songs_by_emotion(self):
        listening_songs = models.EmotionEmotionbasedSong.objects.filter(user=self.user).values('song')
        return listening_songs

    def _get_listening_songs_by_relevant(self):
        listening_songs = models.EmotionRelevantSong.objects.filter(user=self.user).values('song')
        return listening_songs

    def _get_exclude_cluster_songs(self, listening_songs, emotion):
        emotion_order_map = {1: "-pop", 2: "-ballad", 3: "-rock"}
        cluster_songs = models.SearchMusicCluster.objects.exclude(song_id__in=listening_songs).order_by(emotion_order_map[emotion]).values('song')

        return cluster_songs

    def get_listening_songs(self, emotion_map, emotions):
        """
        視聴済みの楽曲取得
        """
        listening_songs = models.EmotionRelevantSong.objects.filter(user=self.user).values('song')
        extra_column = self._get_extra_column(emotion_map, emotions)
        results = models.Song.objects.filter(id__in=listening_songs).extra(select = {'value': extra_column}).values()
        return self._get_song_and_tag_map(results)

    def _get_song_and_tag_map(self, song_objs):

        tags = self._get_tags()
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

        self._change_list_into_numpy(song_tag_map)
        return songs, song_tag_map

    def get_song_tag_map_by_song_ids(self, song_ids, emotion_map, emotions):
        """
        楽曲のid配列から{song: tags}の辞書配列取得
        """
        extra_column = self._get_extra_column(emotion_map, emotions)
        results = models.Song.objects.filter(id__in=song_ids).extra(select = {'value': extra_column}).values()
        return self._get_song_and_tag_map(results)

    def _get_tags(self):
        """
        @return(tags): [tag_name]
        """
        tag_obj = models.Tag.objects.all()
        tags = [tag.name for tag in tag_obj]
        return tags

    def _get_tags_exclude_cluster(self, cluster):
        """
        clusterに所属しないタグのみ取得
        """
        tag_obj = models.SearchTag.objects.exclude(cluster=cluster_map[cluster])
        tags = [tag.name for tag in tag_obj]
        return tags

    def get_song_and_cluster(self):
        songs = models.Song.objects.all().values()
        song_map = {}
        for song in songs:
            song_map[song["id"]] = song
        return song_map

    def _get_upper_songs(self, feedback_cluster, value, bound):
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

    def _get_lower_songs(self, feedback_cluster, value, bound):
        """
        特定の印象ベクトルが特定の値より小さいものを取得
        """
        print "feedback is minus"
        if feedback_cluster == 1:
            return models.SearchMusicCluster.objects.order_by("pop").filter(pop__lte=value, pop__gte=value-bound)
        elif feedback_cluster == 2:
            return models.SearchMusicCluster.objects.order_by("ballad").filter(ballad__lte=value, ballad__gte=value-bound)
        else:
            return models.SearchMusicCluster.objects.order_by("rock").filter(rock__lte=value, rock__gte=value-bound)

    def get_bound_song_tag_map(self, feedback_cluster, value, k, plus_or_minus):

        songs = self._get_bound_songs(feedback_cluster, value, plus_or_minus)
        song_ids = []
        for song in songs[:k]:
            song_ids.append(song.song_id)

        song_objs = models.Song.objects.filter(id__in=song_ids).values()
        return self._get_song_and_tag_map(song_objs)

    def get_bound_with_attenuation_song_tag_map(self, feedback_cluster, top_song_obj, emotion_map, emotions, value, plus_or_minus, bound):
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
        m_objs, songs = self._get_bound_songs(feedback_cluster, value, bound, plus_or_minus)
        count = 0
        print "top_song feedback_cluster value: %.5f" % (value)
        top_song = self._get_song_by_musiccluster(top_song_obj)
        print len(songs)
        song_ids = []
        degree = len(songs[0])
        """
        feedback_clusterに所属するタグ以外のタグ間の距離を比較する
        全てのタグを比較してしまうと、feedback_clusterに該当する値の離れた楽曲が外れてしまうため
        """
        distances = [(m_obj.__dict__[cluster_map[feedback_cluster]] / cy_calc.get_euclid_distance(song, top_song, degree), m_obj.song_id) for m_obj, song in zip(m_objs, songs)]
        distances.sort()
        distances.reverse()
        # count = 0
        # max_value = sum([d[0] for d in distances])
        # for i in xrange(100):
        #     song_id = self.select_train_song(max_value, distances)
        #     if song_id not in song_ids:
        #         song_ids.append(song_id)
        #         count += 1
        #     if count == 10:
        #         break
        for i, distance in enumerate(distances):
            if i == top_k:
                break
            song_ids.append(distance[1])
        extra_column = self._get_extra_column(emotion_map, emotions)
        song_objs = models.Song.objects.filter(id__in=song_ids).extra(select = {'value': extra_column}).values()
        #song_objs = s.extra(order_by=["-value"]).values()[:top_k]
        return self._get_song_and_tag_map(song_objs)

    def select_train_song(self, max_value, distances):
        """
        選択ルーレット方式による学習データの選択
        """
        pick = random.uniform(0, max_value)
        current = 0.0
        for d in distances:
            current += d[0]
            if current > pick:
                return d[1]

    def select_initial_song(self, max_value, songs, song_tag_map):
        """
        選択ルーレット方式による初期検索楽曲の選択
        """
        pick = random.uniform(0, max_value)
        current = 0.0
        for song in songs:
            current += song_tag_map[song][43]
            if current > pick:
                return song

    def _is_upper_bound(self, song_obj, emotion, value, bound):
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

    def _get_bound_songs(self, feedback_cluster, value, bound, plus_or_minus):
        """
        feedback_clusterカラムに対応する値がvalueよりも+or-方向に満たす楽曲を取得
        @returns(m_objs): SearchMusicClusterオブジェクト
        @returns(songs): Songオブジェクト
        """
        if plus_or_minus == 1:
            m_objs = self._get_upper_songs(feedback_cluster, value, bound)
        else:
            m_objs = self._get_lower_songs(feedback_cluster, value, bound)
            m_objs = m_objs.reverse()
        
        songs = self._get_songs_by_musicclusters(feedback_cluster, m_objs)
        return m_objs, songs

    def _get_songs_by_musicclusters(self, feedback_cluster, m_objs):
        """
        SearchMusicClusterからsong_tags配列取得
        """
        tags = self._get_tags_exclude_cluster(feedback_cluster)
        songs = np.zeros((len(m_objs), len(tags)))
        for m_index, m_obj in enumerate(m_objs):
            song_obj = m_obj.song.__dict__
            for index, tag in enumerate(tags):
                songs[m_index][index] = song_obj[tag]

        return songs

    def _get_song_by_musiccluster(self, m_obj):
        """
        SearchMusicClusterオブジェクトから{song: tags[]}取得
        """
        tags = self._get_tags()
        song = np.zeros(43)
        song_obj = m_obj.song.__dict__
        for index, tag in enumerate(tags):
            song[index] = song_obj[tag]

        return song

    def _change_list_into_numpy(self, target_map):
        """
        listを持つdictをnumpy.arrayに変換
        """
        for key, values in target_map.items():
            target_map[key] = np.array(values)

    def listtuple_sort_reverse(self, t):
        """
        タプルを要素として持つリストのソートして逆順にする
        """
        t.sort()
        t.reverse()

    def write_top_k_songs_emotion(self, filepass, top_k_songs, emotion_map, emotions, feedback_type = "", plus_or_minus = 0):
        """
        上位k個の楽曲のファイルへの書き込み
        """
        print "write emotion songs"
        user_id = str(self.user).encode('utf-8')
        filepass = user_id + "_" + filepass
        f = codecs.open("file/" + filepass, "a")
        feedback_type = feedback_type.encode('utf-8')
        #emotion = emotion_map[emotions[0]].encode('utf-8')
        if plus_or_minus == 1:
            f.write("user: " + user_id + " feedback_type: ↑" + feedback_type + " emotion: ")
        elif plus_or_minus == -1:
            f.write("user: " + user_id + " feedback_type: ↓" + feedback_type + " emotion: ")
        else:
            f.write("user: " + user_id + " feedback_type: " + feedback_type + " emotion: ")
        if emotions != None:
            for emotion in emotions:
                f.write(emotion_map[emotion] + ",")
        f.write("\n")
        f.write("predict_value, song_id, pop, ballad, rock\n")
        for song in top_k_songs:
            song_obj = self._get_music_cluster_value(song[1])
            content = str(song) + "," + str(song_obj["pop"]) + "," + str(song_obj["ballad"]) + "," + str(song_obj["rock"]) + "\n"
            f.write(content)
        f.write("\n")
        f.close()

    def write_top_k_songs_relevance(self, filepass, top_k_songs, emotion_map, emotions, feedback):
        """
        適合性フィードバックにおける上位k曲のファイルへの書き込み
        """
        print "write relevance songs"
        user_id = str(self.user).encode('utf-8')
        feedback = str(feedback).encode('utf-8')
        filepass = user_id + "_" + filepass
        f = codecs.open("file/" + filepass, "a")
        f.write("user: " + user_id + " feedback_type:" + feedback + " emotions: ")
        if emotions != None:
            for emotion in emotions:
                f.write(emotion_map[emotion] + ",")
        f.write("\n")
        for song in top_k_songs:
            song_obj = self._get_music_cluster_value(song[1])
            content = str(song) + "," + str(song_obj["pop"]) + "," + str(song_obj["ballad"]) + "," + str(song_obj["rock"]) + "\n"
            f.write(content)
        f.write("\n")
        f.close()

    def write_top_k_songs_init(self, filepass, top_k_songs, emotion_map, situation, emotions):
        """
        初期検索時のtop_5楽曲保存
        """
        print "write init songs"
        user_id = str(self.user).encode('utf-8')
        situation = str(situation).encode('utf-8')
        filepass = user_id + "_" + filepass
        f = codecs.open("file/" + filepass, "a")
        f.write("user: " + user_id +  " situation: " + situation + " emotions: ")
        if emotions != None:
            for emotion in emotions:
                f.write(emotion_map[emotion] + ",")
        f.write("\n")
        for song in top_k_songs:
            song_obj = self._get_music_cluster_value(song)
            content = str(song) + "," + str(song_obj["pop"]) + "," + str(song_obj["ballad"]) + "," + str(song_obj["rock"]) + "\n"
            f.write(content)
        f.write("\n")
        f.close()

    def _get_music_cluster_value(self, song_id):
        top_song_objs = models.SearchMusicCluster.objects.filter(song_id=int(song_id)).values()[0]
        return top_song_objs


class CommonRandomFunctions(CommonFunctions):
    """
    検索条件なしの時のクラス
    """
    def __init__(self, user):
        CommonFunctions.__init__(self, user)

    def _set_listening_songs(self):
        self.songs, self.song_tag_map = self.cf_obj.get_listening_songs()

    def get_initial_not_listening_songs(self, emotion_map, feedback_type):
        """
        未視聴の楽曲を取得
        初期検索時に使用
        """
        print "未視聴の楽曲取得"
        listening_songs = self._get_listening_songs_by_feedback_type(feedback_type)
        song_objs = models.Song.objects.exclude(id__in=listening_songs).values()
        return self._get_song_and_tag_map(song_objs)

    def get_not_listening_songs(self, feedback_type = "relevant"):
        """
        未視聴の楽曲を取得
        初期検索以降の際に使用
        """
        print "未視聴の楽曲取得"
        listening_songs = self._get_listening_songs_by_feedback_type(feedback_type)
        cluster_songs = models.SearchMusicCluster.objects.exclude(song_id__in=listening_songs).values("song")
        results = self._get_song_obj_by_cluster_songs(cluster_songs)
        return self._get_song_and_tag_map(results)
    
    def _get_song_obj_by_cluster_songs(self, cluster_songs):
        top_k_songs = []
        for song in cluster_songs:
            top_k_songs.append(song["song"])
            
        results = models.Song.objects.filter(id__in=top_k_songs).values()
        
        return results

    def get_bound_with_attenuation_song_tag_map(self, feedback_cluster, top_song_obj, value, plus_or_minus, bound):
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
        m_objs, songs = self._get_bound_songs(feedback_cluster, value, bound, plus_or_minus)
        count = 0
        print "top_song feedback_cluster value: %.5f" % (value)
        top_song = self._get_song_by_musiccluster(top_song_obj)
        print len(songs)
        song_ids = []
        degree = len(songs[0])
        """
        feedback_clusterに所属するタグ以外のタグ間の距離を比較する
        全てのタグを比較してしまうと、feedback_clusterに該当する値の離れた楽曲が外れてしまうため
        """
        distances = [(m_obj.__dict__[cluster_map[feedback_cluster]] / cy_calc.get_euclid_distance(song, top_song, degree), m_obj.song_id) for m_obj, song in zip(m_objs, songs)]
        distances.sort()
        distances.reverse()
        for i, distance in enumerate(distances):
            if i == top_k:
                break
            song_ids.append(distance[1])
        song_objs = models.Song.objects.filter(id__in=song_ids).values()
        return self._get_song_and_tag_map(song_objs)

    def _get_song_and_tag_map(self, song_objs):

        tags = self._get_tags()
        song_tag_map = {} # {song_id: List[tag_value]}
        songs = [] # List[song_id]
        for song_obj in song_objs:
            song_id = song_obj['id']
            songs.append(song_id)
            song_tag_map.setdefault(song_id, [])
            for tag in tags:
                song_tag_map[song_id].append(song_obj[tag])
            # クエリに関する特徴量を追加

        self._change_list_into_numpy(song_tag_map)
        return songs, song_tag_map

    def get_listening_songs(self):
        """
        視聴済みの楽曲取得
        """
        listening_songs = models.EmotionRelevantSong.objects.filter(user=self.user).values('song')
        results = models.Song.objects.filter(id__in=listening_songs).values()
        return self._get_song_and_tag_map(results)

    def get_song_tag_map_by_song_ids(self, song_ids):
        """
        楽曲のid配列から{song: tags}の辞書配列取得
        """
        results = models.Song.objects.filter(id__in=song_ids).values()
        return self._get_song_and_tag_map(results)
    
    def get_now_order(self, situation, feedback_type):
        """
        現在何曲目かを取得
        """
        count = models.SearchSong.objects.filter(user_id=self.user, situation=situation, feedback_type=feedback_type).count()
        return count+1
