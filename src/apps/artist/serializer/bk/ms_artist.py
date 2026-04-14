from rest_framework import serializers

# --- アーティストモジュール ---
from apps.artist.models import T_Artist, M_ArtistTag, M_ArtistContext

class MS_ArtistSerializer(serializers.ModelSerializer):
    """参照用（レスポンス用）シリアライザー"""
    class Meta:
        model = T_Artist
        fields = '__all__' # 必要に応じて調整
        depth = 1 # 紐づく画像やコンテキストの詳細まで出す場合


class MS_ArtistCreateSerializer(serializers.Serializer):
    """アーティスト登録用シリアライザー"""
    # Spotifyからのデータ(ネストして受け取ると管理しやすい)
    spotify_id = serializers.CharField(max_length=255)
    name = serializers.CharField(max_length=255)
    image_url = serializers.URLField(required=False, allow_null=True)
    genres = serializers.ListField(child=serializers.CharField(), required=False, default=list)

    # ※PrimaryKeyRelatedFieldを利用
    # serializers.PrimaryKeyRelatedFieldのqueryset にフィルタをかけている場合、
    # DRFはバリデーション時(is_valid()実行時)に以下の挙動を行う
    # 1. DB問い合わせ: 送られてきたIDが、指定されたqueryset内に既に存在するか確認(論理削除も考慮)
    # 2. 自動エラー応答: 存在しない(または論理削除済み)IDだった場合、DRFは自動的に「400 Bad Request」を返す
    context_id = serializers.PrimaryKeyRelatedField(
        queryset=M_ArtistContext.objects.filter(deleted_at__isnull=True),
        required=False,
        allow_null=True,
    )
    tag_ids = serializers.PrimaryKeyRelatedField(
        queryset=M_ArtistTag.objects.filter(deleted_at__isnull=True),
        many=True,
        required=False,
    )
