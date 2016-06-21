# -*- coding:utf-8 -*-
import sys
sys.dont_write_bytecode = True 
import recommend

def create_recommend_obj(user, K):

    rm_obj = recommend.RecommendFm(user, K)
    return rm_obj

def get_top_song(rm_obj):

    top_song = rm_obj.get_top_song()
    return top_song

def get_rankings(rm_obj, rank):

    rankings = rm_obj.get_rankings(rank)
    return rankings
