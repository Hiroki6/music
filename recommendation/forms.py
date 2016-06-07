from django import forms

class MusicSearchForm(forms.Form):
    artist = forms.CharField(required=False, max_length=100)
    song = forms.CharField(required=False, max_length=100)
