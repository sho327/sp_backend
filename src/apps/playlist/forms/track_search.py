from django import forms
from unfold.widgets import UnfoldAdminTextInputWidget, UnfoldAdminSelectWidget

LIMIT_CHOICES = [(i, str(i)) for i in range(1, 11)]

class TrackSearchForm(forms.Form):
    search_artist_name = forms.CharField(
        label="アーティスト名",
        required=False, 
        max_length=255,
        widget=UnfoldAdminTextInputWidget(attrs={"placeholder": "例: YOASOBI"})
    )
    search_track_name = forms.CharField(
        label="曲名",
        required=False, 
        max_length=255,
        widget=UnfoldAdminTextInputWidget(attrs={"placeholder": "例: 夜に駆ける"})
    )
    limit = forms.TypedChoiceField(
        label="取得件数",
        required=False, 
        choices=LIMIT_CHOICES,
        coerce=int,
        initial=10,
        widget=UnfoldAdminSelectWidget()
    )

    def clean(self):
        cleaned_data = super().clean()
        artist = cleaned_data.get("search_artist_name")
        track = cleaned_data.get("search_track_name")
        
        # アーティスト名も曲名も入力されていない場合はエラー
        if not artist and not track:
            # self.add_error("search_artist_name", "アーティスト名または曲名のいずれかを入力してください。")
            raise forms.ValidationError("アーティスト名または曲名のいずれかを入力してください。")
            
        return cleaned_data
