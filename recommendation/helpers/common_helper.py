# -*- coding:utf-8 -*-

def get_feedback_dict():

    feedbacks = ["calm", "tense", "aggressive", "lively", "peaceful"]
    feedback_dict = {}
    for i in xrange(2):
        for index, feedback in enumerate(feedbacks):
            key = i * 5 + index
            feedback_dict[key] = feedback

    return feedback_dict

