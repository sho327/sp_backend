from rest_framework import serializers
from apps.artist.models import M_ArtistTag, M_ArtistContext

class Model_T_ArtistCreateSerializer(serializers.Serializer):
    """アーティスト登録用シリアライザー"""
    # Spotifyからのデータ(ネストして受け取ると管理しやすい)
    spotify_id = serializers.CharField(max_length=255)
    name = serializers.CharField(max_length=255)
    image_url = serializers.URLField(required=False, allow_null=True)
    genres = serializers.ListField(child=serializers.CharField(), required=False, default=list)

    # 自社マスタとの紐付け
    context_id = serializers.PrimaryKeyRelatedField(
        queryset=M_ArtistContext.objects.filter(deleted_at__isnull=True),
        required=False,
        allow_null=True
    )
    tag_ids = serializers.PrimaryKeyRelatedField(
        queryset=M_ArtistTag.objects.filter(deleted_at__isnull=True),
        many=True,
        required=False
    )
