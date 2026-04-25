from django import forms

from apps.artist.models import T_Artist

class ArtistSearchForm(forms.Form):
    q = forms.CharField(required=False, max_length=255)
    limit = forms.IntegerField(required=False, min_value=1, max_value=10, initial=10)
