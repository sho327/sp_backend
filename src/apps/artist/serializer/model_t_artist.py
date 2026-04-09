from rest_framework import serializers
from apps.artist.models import T_Artist

class Model_T_ArtistSerializer(serializers.ModelSerializer):
    """参照用（レスポンス用）シリアライザー"""
    class Meta:
        model = T_Artist
        fields = '__all__' # 必要に応じて調整
        depth = 1 # 紐づく画像やコンテキストの詳細まで出す場合
