# -*- coding:utf-8 -*-
from django import forms

class MusicSearchForm(forms.Form):
    artist = forms.CharField(required=False, max_length=100)
    song = forms.CharField(required=False, max_length=100)

EMOTION_CHOICE = (('1', '静かな楽曲', '2', '激しい楽曲'))
class EmotionSearchForm(forms.Form):
    #term = forms.CharField(required=False, max_length=100)
    term = forms.ChoiceField(widget=forms.RadioSelect, choices=EMOTION_CHOICE)
