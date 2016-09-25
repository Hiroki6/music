# -*- coding:utf-8 -*-
import sys
sys.dont_write_bytecode = True 
import recommend

def create_recommend_obj(user, K):

    rm_obj = recommend.RecommendFm(user, K)
    return rm_obj

def get_top_song(rm_obj):

    rm_obj.get_matrixes_by_song()
    top_song = rm_obj.get_top_song_cython()
    return top_song

def get_rankings(rm_obj):
    
    rm_obj.get_matrixes_by_song()
    rankings = rm_obj.get_rankings(10)
    return rankings
