# -*- coding:utf-8 -*-

"""
印象語検索における印象語フィードバックによるモデルの学習
モデルのパラメータは事前にredisに保存してある
"""

class EmotionSearch:
    def __init__(self):
        self._get_params_by_redis()
        return

    def _get_params_by_redis(self):
        return
