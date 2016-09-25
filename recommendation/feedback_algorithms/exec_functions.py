# -*- coding:utf-8 -*-

"""
helperから呼ばれる各オブジェクト実行用の関数
"""
import relevant_feedback as r_f

def get_song_by_relevant(user, emotion):
    r_obj = r_f.RelevantFeedback(user, emotion)
    song = r_obj.get_recommend_songs()
    return song
