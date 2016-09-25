# -*- coding:utf-8 -*-

"""
helperから呼ばれる各オブジェクト実行用の関数
"""
import relevant_feedback as r_f

def get_song_by_relevant(user, emotion):
    r_obj = r_f.RelevantFeedback(user, emotion)
    top_k_songs = r_obj.get_top_k_songs()
    song_ids = [song[1] for song in top_k_songs]
    return song_ids
