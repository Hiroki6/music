# -*- coding:utf-8 -*-

import numpy as np
import pandas as pd
from sklearn.feature_extraction import DictVectorizer
import random
from .. import models
import sys
sys.dont_write_bytecode = True 
from django.contrib.auth.models import User
import os.path

BASE = os.path.dirname(os.path.abspath(__file__))

def get_song_tags():

    results = models.Song.objects.all().values()
    tag_obj = models.Tag.objects.all()
    tags_map = {}
    for index, tag in enumerate(tag_obj):
        tags_map[tag.name] = index

    song_tag_map = {}

    for result in results:
        song_id = str(result["id"])
        song_tag_map.setdefault(song_id, np.zeros(len(tags_map)))
        for tag, tag_value in result.items():
            if tags_map.has_key(tag):
                song_tag_map[song_id][tags_map[tag]] = tag_value

    return song_tag_map

def get_all_song_id_set():

    song_nums = models.Song.objects.count()
    songs = np.arange(song_nums)+1
    songs = songs.astype(str)
    songs = set(songs)
    return songs

"""
return(rate_matrix) FM用のデータ
userとsongとartist名とtagを用いる
rate_matrix, test_matrix, labels, targets, tag_map, ratelist
@params(learn_matrix): 学習用データ(FMフォーマット)
@params(regs_matrix): 正規化パラメータ決定のための交差regsデータ(FMフォーマット)
@params(labels): 学習用データラベル
@params(targets): 教師ラベル 1次元np.array
@params(tag_map): {インデックス: 教師データ上のインデックス}
@params(ratelist): {user: songs[]}
"""
def create_matrix_with_tag_dicVec():

    ratelist = get_ratelist() # {user: [songs]}
    song_tags = get_song_tags() # {song: [tags]}
    all_song_set = get_all_song_id_set() # 楽曲のidの集合
    already_song_set = set() # すでに出現した楽曲
    tags = get_tags()
    rate_array= []
    tag_map = {} # {tag: tag_index}
    targets = [] # 教師データ

    print "正規化項用データ作成"
    regs_data = {}
    regs_num = int(len(ratelist) * 0.05)
    for i in xrange(regs_num):
        user = random.choice(ratelist.keys())
        index = random.randint(0, len(ratelist[user])-1)
        song = ratelist[user].pop(index)
        if not regs_data.has_key(user):
            regs_data.setdefault(user, [])
        regs_data[user].append(song)

    print "学習用データ作成"
    for user, songs in ratelist.items():
        for song in songs:
            if not song_tags.has_key(song):
                already_song_set.add(song)
                continue
            rate_dic = {}
            rate_dic["user"] = user
            rate_dic["song"] = song
            if song not in already_song_set:
                already_song_set.add(song)
            for tag, value in zip(tags, song_tags[song]):
                rate_dic[tag] = float(value)
            targets.append(1)
            rate_array.append(rate_dic)
    
    print "楽曲補充"
    # 視聴履歴に含まれていない楽曲を入れる
    all_song_set.difference_update(already_song_set)
    for song in all_song_set:
        rate_dic = {}
        rate_dic["user"] = user
        rate_dic["song"] = song
        for tag, value in zip(tags, song_tags[song]):
            rate_dic[tag] = float(value)
        rate_array.append(rate_dic)

    v = DictVectorizer()
    X = v.fit_transform(rate_array)
    rate_matrix = X.toarray()
    labels = v.get_feature_names()
    data_labels = dict(zip(labels, range(0, len(labels))))
    targets = np.array(targets)
    for index, tag in enumerate(tags):
        tag_map[index] = data_labels[tag]
    
    print "正規化用データ変形"
    regs_matrix = create_regs_matrix(regs_data, data_labels, tag_map, regs_num)

    return rate_matrix[:len(targets)], regs_matrix, data_labels, targets, tag_map, ratelist

"""
テストデータのFM配列作成
"""
def create_regs_matrix(test_data, data_labels, tag_map, test_nums):

    song_tags = get_song_tags()
    test_matrix = np.zeros((test_nums, len(data_labels)))
    col = 0
    for user, songs in test_data.items():
        user_index = data_labels["user="+user]
        not_learn_songs = []
        for index, song in enumerate(songs):
            song_label_name = "song=" + song
            if not data_labels.has_key(song_label_name):
                not_learn_songs.append(song)
            else:
                song_index = data_labels[song_label_name]
                test_matrix[col][user_index] = 1.0
                test_matrix[col][song_index] = 1.0
                for tag_index, tag_value in enumerate(song_tags[song]):
                    test_matrix[col][tag_map[tag_index]] = tag_value
                col += 1
        for not_learn_song in not_learn_songs:
            test_data[user].remove(not_learn_song)
    test_matrix = test_matrix[:col]

    return test_matrix

def get_ratelist():

    rate_dic = {}

    for line in open(os.path.join(BASE, "../data_10/song_listening_data_10.csv")):
        rate = line.replace("\n","").split(',')
        user = rate[0]
        song_id = rate[1]
        if not rate_dic.has_key(user):
            rate_dic.setdefault(user, [])
        rate_dic[user].append(song_id)
    
    app_preferences = models.Preference.objects.all()
    for app_preference in app_preferences:
        user = str(app_preference.user_id)
        song_id = str(app_preference.song_id)
        if not rate_dic.has_key(user):
            rate_dic.setdefault(user, [])
        rate_dic[user].append(song_id)

    return rate_dic

def get_tags():

    tag_obj = models.Tag.objects.all()
    tags = []
    for tag in tag_obj:
        tags.append(tag.name)

    return tags
