# -*- coding:utf-8 -*-
import sys
sys.dont_write_bytecode = True 
from Recommend import recommend

def create_recommend_obj(user, K):

    rm_obj = recommend.RecommendFm(user, K)
    return rm_obj

def get_top_song(rm_obj):

    top_value, top_song, top_matrix = rm_obj.get_top_song()
    return top_value, top_song, top_matrix

def get_rankings(rm_obj, rank):

    rankings = rm_obj.get_rankings(rank)
    return rankings
