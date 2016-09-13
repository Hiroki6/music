# -*- coding:utf-8 -*-

"""
印象語検索におけるフィードバックによるモデルの学習
モデルのパラメータは事前にredisに保存してある
"""

feedback_method_map = {"relevant": 0, "emotion": 1}

class EmotionSearch:
    """
    feedback_method: {適合性フィードバック: 0, 印象語によるフィードバック: 1}
    """
    def __init__(self, feedback_method = "relevant"):
        self.feedback_method = feedback_method_map[feedback_method]
        self._get_params_by_redis()
        return

    def _get_params_by_redis(self):
        return
