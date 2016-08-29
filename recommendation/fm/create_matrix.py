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

"""
ラベルの作成
"""
def get_data_labels_and_tag_map():

    labels = []
    tag_map = {}
    tags = get_tags()
    songs = get_uniq_songs()
    users = get_uniq_users()
    for tag in tags:
        labels.append(tag)
    
    for song in songs:
        labels.append("song="+song)

    for user in users:
        labels.append("user="+user)
    
    data_labels = dict(zip(labels, range(0, len(labels))))

    for index, tag in enumerate(tags):
        tag_map[index] = data_labels[tag]

    return data_labels, tag_map

def create_fm_matrix():

    data_labels, tag_map = get_data_labels_and_tag_map()
    ratelist, rate_nums, regs_data, regs_nums = get_ratelist() # {user: [songs]}

    print "学習用データ変形"
    rate_matrix = transform_matrix(ratelist, data_labels, tag_map, rate_nums)
    print "正規化用データ変形"
    regs_matrix = transform_matrix(regs_data, data_labels, tag_map, regs_nums)

    targets = np.ones(len(rate_matrix), dtype=np.int64)

    return rate_matrix, regs_matrix, data_labels, targets, tag_map, ratelist

def get_uniq_users():
   
    uniq_users = []
    with open(os.path.join(BASE, "../data_10/uniq_user.csv")) as f:
        for line in f:
            user = line.replace("\n","")
            uniq_users.append(user)

    for users in models.Preference.objects.values("user_id").distinct():
        uniq_users.append(str(users["user_id"]))

    return uniq_users

def get_uniq_songs():

    uniq_songs = []
    for song in models.Song.objects.values("id").distinct():
        uniq_songs.append(str(song["id"]))

    return uniq_songs

"""
FMの配列の形に変形
"""
def transform_matrix(test_data, data_labels, tag_map, test_nums):

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

    rate_dic, rate_nums = get_dic_and_nums_by_file("../data_10/train.csv")

    app_preferences = models.Preference.objects.all()
    for app_preference in app_preferences:
        user = str(app_preference.user_id)
        song_id = str(app_preference.song_id)
        if not rate_dic.has_key(user):
            rate_dic.setdefault(user, [])
        rate_dic[user].append(song_id)
        rate_nums += 1

    regs_dic, regs_nums = get_dic_and_nums_by_file("../data_10/regulation.csv")

    return rate_dic, rate_nums, regs_dic, regs_nums

"""
fileから視聴履歴の辞書と視聴数を取得する
"""
def get_dic_and_nums_by_file(filepass, validation_songs = None):

    dic = {}
    nums = 0
    for line in open(os.path.join(BASE, filepass)):
        rate = line.replace("\n","").split(',')
        user = rate[0]
        song_id = rate[1]
        if validation_songs is not None and song_id in validation_songs:
            continue
        if not dic.has_key(user):
            dic.setdefault(user, [])
        dic[user].append(song_id)
        nums += 1

    return dic, nums

def get_tags():

    tag_obj = models.Tag.objects.all()
    tags = []
    for tag in tag_obj:
        tags.append(tag.name)

    return tags

def get_cross_validation_song():

    uniq_songs = []
    validation_songs = []
    with open(os.path.join(BASE, "../data_10/uniq_songs.csv")) as f:
        for line in f:
            contents = line.replace("\n","").split(",")
            song = contents[0]
            uniq_songs.append(song)

    validation_nums = int(len(uniq_songs) * 0.2)
    
    for i in xrange(validation_nums):
        index = random.randint(0, len(uniq_songs)-1)
        song = uniq_songs.pop(index)
        validation_songs.append(song)

    return uniq_songs, validation_songs

"""
スムージングの精度評価用の配列作成
"""
def create_smoothing_fm_matrix():

    train_songs, validation_songs = get_cross_validation_song()

    rate_matrix, regs_matrix, labels, targets, tag_map, ratelist = create_fm_matrix()

    return rate_matrix, regs_matrix, labels, targets, tag_map, ratelist, train_songs, validation_songs
