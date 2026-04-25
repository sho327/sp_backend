from django import forms
from unfold.widgets import UnfoldAdminTextInputWidget, UnfoldAdminSelectWidget

LIMIT_CHOICES = [(i, str(i)) for i in range(1, 11)]

class ArtistSearchForm(forms.Form):
    q = forms.CharField(
        label="アーティスト名",
        required=False, 
        max_length=255,
        widget=UnfoldAdminTextInputWidget(attrs={"placeholder": "例: YOASOBI"})
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
        q = cleaned_data.get("q")
        
        # アーティスト名が入力されていない場合はエラー
        if not q:
            # self.add_error("q", "アーティスト名を入力してください。")
            raise forms.ValidationError("アーティスト名を入力してください。")
            
        return cleaned_data
