from django import forms
from unfold.widgets import UnfoldAdminTextInputWidget, UnfoldAdminIntegerFieldWidget

class ArtistSearchForm(forms.Form):
    q = forms.CharField(
        label="アーティスト名",
        required=False, 
        max_length=255,
        widget=UnfoldAdminTextInputWidget(attrs={"placeholder": "例: YOASOBI"})
    )
    limit = forms.IntegerField(
        label="取得件数",
        required=False, 
        min_value=1, 
        max_value=20, 
        initial=10,
        widget=UnfoldAdminIntegerFieldWidget()
    )
