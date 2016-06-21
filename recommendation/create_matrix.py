# -*- coding:utf-8 -*-

import numpy as np
import pandas as pd
from sklearn.feature_extraction import DictVectorizer
import random
import MySQLdb
from .models import *
import sys
sys.dont_write_bytecode = True 

"""
@return(song_map) {"アーティスト名":"曲名":id}の辞書
"""
def create_song_map():

    song_map = {}
    idx = 0
    for line in open("../musicdata_5/uniq_songs.csv"):
        artist = line.replace("\n","").split(',')[0]
        song = line.replace("\n","").split(',')[1]
        if not song_map.has_key(artist):
            song_map.setdefault(artist, {})
        song_map[artist][song] = str(idx)
        idx += 1

    return song_map, idx+1

"""
@return(song_map) {"アーティスト名":"曲名":id}の辞書
"""
def get_song_map():

    song_map = {}
    idx = 0
    for line in open("../musicdata_5/uniq_songs.csv"):
        artist = line.replace("\n","").split(',')[0]
        song = line.replace("\n","").split(',')[1]
        if not song_map.has_key(artist):
            song_map.setdefault(artist, {})
        song_map[artist][song] = str(idx)
        idx += 1

    return song_map, idx+1


"""
@return(user_map) {"値":id}の辞書
"""
def create_user_map():

    user_map = {}
    idx = 0
    for line in open("../musicdata_5/user.csv"):
        user = line.replace("\n","")
        user_map[user] = str(idx)
        idx += 1

    return user_map

"""
return(rate_matrix) FM用のデータ
userとartistとsongのみを扱う
"""
def create_matrix_dicVec():

    usermap = create_user_map()
    itemmap, item_count = create_song_map()
    ratelist = create_ratelist()
    
    rate_array= []
    targets = [] # 教師データ
    for rate in ratelist:
        rate_dic = {}
        rate_dic["user"] = usermap[rate[0]]
        rate_dic["item"] = itemmap[rate[1]][rate[2]]
        targets.append(1)
        rate_array.append(rate_dic)
  
    v = DictVectorizer()
    X = v.fit_transform(rate_array)
    rate_matrix = X.toarray()
    labels = v.get_feature_names()
    targets = np.array(targets)

    return rate_matrix, labels, targets

def get_song_tags():

    songs = []
    songmap, _ = create_song_map()
    for line in open("../musicdata_5/uniq_songs_tag.csv"):
        songs.append(line.replace("\n","").split(","))
    
    song_tags = {}
    for song in songs:
        artist = song[0]
        songName = song[1]
        song_index = str(songmap[artist][songName])
        song_tags.setdefault(song_index, [])
        for index in range(2,len(song)):
            song_tags[song_index].append(song[index])

    return song_tags

def get_all_tags(filepass):

    tags = []
    with open(filepass) as f:
        for line in f:
            tag = line.replace("\n","").replace("\r","")
            tags.append(tag)

    return tags

def get_test_users():

    userlist = create_element("../musicdata_5/user.csv")
    test_users = []
    usermap = create_user_map()
    number_of_test = int(len(userlist) * 0.2)
    for i in xrange(number_of_test):
        index = random.randint(0, len(userlist)-1)
        user = userlist.pop(index)
        test_users.append(str(usermap[user]))

    return test_users

    
"""
return(rate_matrix) FM用のデータ
userとsongとartist名とtagを用いる
rate_matrix, test_matrix, test_data, labels, targets, tag_map, ratelist
@params(learn_matrix): 学習用データ(FMフォーマット)
@params(regs_matrix): 正規化パラメータ決定のための交差regsデータ(FMフォーマット)
@params(test_data): テストデータ({user: song[]})
@params(labels): 学習用データラベル
@params(targets): 教師ラベル 1次元np.array
@params(tag_map): {インデックス: 教師データ上のインデックス}
@params(ratelist): {user: songs[]}
"""
def create_matrix_with_tag_dicVec():

    usermap = create_user_map()
    ratelist = create_ratelist()
    song_tags = get_song_tags()
    tags = get_tags()
    #tags = get_all_tags("../LJ2M/music_emotion_tag_in_anew.txt")
    rate_array= []
    tag_map = {} # {tag: tag_index}
    targets = [] # 教師データ
    test_users = get_test_users()
    test_data = {}
    test_nums = 0
    print "テスト用データ作成"
    for user, songs in ratelist.items():
        test_num = int(len(songs) * 0.2)
        test_data.setdefault(user, [])
        test_nums += test_num
        for i in xrange(test_num):
            index = random.randint(0, len(ratelist[user])-1)
            song = ratelist[user].pop(index)
            test_data[user].append(song)

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
    
    regs_matrix = create_test_matrix(regs_data, labels, tag_map, regs_num)
    test_matrix = create_test_matrix(test_data, labels, tag_map, test_nums)

    return rate_matrix, regs_matrix, test_matrix, test_data, labels, targets, tag_map, ratelist

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

def create_element(filename):

    ret = []
    for line in open(filename):
        ret.append(line.replace("\n","").split('::')[0])
    
    return ret

def create_ratelist():

    rate_dic = {}
    songmap, _ = create_song_map()
    usermap = create_user_map()

    for line in open("../musicdata_5/song_listening_data_over_5.csv"):
        rate = line.replace("\n","").split(',')
        user = usermap[rate[0]]
        artist = rate[1]
        song = rate[2]
        song_index = str(songmap[artist][song])
        if not rate_dic.has_key(user):
            rate_dic.setdefault(user, [])
        rate_dic[user].append(song_index)

    return rate_dic

def get_tags():

    connection, cursor = connect_db()

    get_tag_sql = "select * from recommendation_tag"
    cursor.execute(get_tag_sql)
    results = cursor.fetchall()
    close_db(connection, cursor)

    tags = []
    for result in results:
        tags.append(result[1])

    return tags

def get_tags_by_db():

    tag_obj = Tag.objects.all()
    tags = []
    for tag in tag_obj:
        tags.append(tag.name)

    return tags
