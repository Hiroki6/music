# -*- coding:utf-8 -*-

import numpy as np
import pandas as pd
from sklearn.feature_extraction import DictVectorizer
import random
import MySQLdb
from .models import *
import sys
sys.dont_write_bytecode = True 
from django.contrib.auth.models import User
import os.path

BASE = os.path.dirname(os.path.abspath(__file__))

"""
@return(user_map) {"値":id}の辞書
"""
def get_user_map():

    user_map = {}
    idx = 0
    for line in open(os.path.join(BASE, "data/user.csv")):
        user = line.replace("\n","")
        user_map[user] = str(idx)
        idx += 1

    app_users = User.objects.all()
    for app_user in app_users:
        user_map[str(app_user.id)] = str(idx)
        idx += 1
    
    return user_map

def get_song_tags():

    results = SongTag.objects.all().values()
    tag_obj = Tag.objects.all()
    tags_map = {}
    for index, tag in enumerate(tag_obj):
        tags_map[tag.name] = index

    song_tag_map = {}

    for result in results:
        song_id = str(result["id"])
        song_tag_map.setdefault(song_id, np.zeros(len(tags_map)))
        for tag, tag_value in result.items():
            if tag == "id" or tag == "song_id":
                continue
            song_tag_map[song_id][tags_map[tag]] = tag_value

    return song_tag_map

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

    usermap = get_user_map()
    ratelist = get_ratelist()
    song_tags = get_song_tags()
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
                continue
            rate_dic = {}
            rate_dic["user"] = user
            rate_dic["song"] = song
            for tag, value in zip(tags, song_tags[song]):
                rate_dic[tag] = float(value)
            targets.append(1)
            rate_array.append(rate_dic)

    v = DictVectorizer()
    X = v.fit_transform(rate_array)
    rate_matrix = X.toarray()
    labels = v.get_feature_names()
    targets = np.array(targets)
    for index, tag in enumerate(tags):
        tag_index = labels.index(tag)
        tag_map[index] = tag_index
    
    print "正規化用データ変形"
    regs_matrix = create_test_matrix(regs_data, labels, tag_map, regs_num)

    return rate_matrix, regs_matrix, labels, targets, tag_map, ratelist

"""
テストデータのFM配列作成
"""
def create_test_matrix(test_data, data_labels, tag_map, test_nums):

    song_tags = get_song_tags()
    test_matrix = np.zeros((test_nums, len(data_labels)))
    col = 0
    for user, songs in test_data.items():
        user_index = data_labels.index("user="+user)
        not_learn_songs = []
        for index, song in enumerate(songs):
            song_label_name = "song=" + song
            if song_label_name not in data_labels:
                not_learn_songs.append(song)
            else:
                song_index = data_labels.index(song_label_name)
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
    usermap = get_user_map()

    for line in open(os.path.join(BASE, "data/song_listening_data.csv")):
        rate = line.replace("\n","").split(',')
        user = usermap[rate[0]]
        song_id = rate[1]
        if not rate_dic.has_key(user):
            rate_dic.setdefault(user, [])
        rate_dic[user].append(song_id)
    
    app_preferences = Preference.objects.all()
    for app_preference in app_preferences:
        user = usermap[str(app_preference.user_id)]
        song_id = str(app_preference.song_id)
        if not rate_dic.has_key(user):
            rate_dic.setdefault(user, [])
        rate_dic[user].append(song_id)

    return rate_dic

def get_tags():

    tag_obj = Tag.objects.all()
    tags = []
    for tag in tag_obj:
        tags.append(tag.name)

    return tags
