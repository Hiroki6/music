# -*- coding:utf-8 -*-

import random
from recommendation import models

def get_feedback_dict():

    feedbacks = ["calm", "tense", "aggressive", "lively", "peaceful"]
    feedback_dict = {}
    for i in xrange(2):
        for index, feedback in enumerate(feedbacks):
            key = i * 5 + index
            feedback_dict[key] = feedback

    return feedback_dict

def get_random_song():
    number_of_records = models.Song.objects.count()
    random_index = int(random.random()*number_of_records)+1
    song = models.Song.objects.filter(id = random_index).values()
    return song
