from rest_framework import serializers

# --- アーティストモジュール ---
from apps.artist.models import T_Artist

class TrackRequestSerializer(serializers.Serializer):
    """
    入力：フロントエンドから送られてくるデータの検品
    """
    name = serializers.CharField(required=True)
    spotify_id = serializers.CharField(required=True)
    artist_name = serializers.CharField(required=True)
    artist_spotify_id = serializers.CharField(required=True)
    artist_spotify_image_url = serializers.URLField(required=True)
    artist_genres = serializers.ListField(child=serializers.CharField(), required=True)

class PlaylistCreateRequestSerializer(serializers.Serializer):
    """
    入力：フロントエンドから送られてくるデータの検品
    ※バイナリ画像を扱うため、Multipartリクエスト専用
    """

    title = serializers.CharField(required=True)
    image = serializers.ImageField()
    spotify_id = serializers.CharField(required=True)
    # ※PrimaryKeyRelatedFieldを利用
    # serializers.PrimaryKeyRelatedFieldのqueryset にフィルタをかけている場合、
    # DRFはバリデーション時(is_valid()実行時)に以下の挙動を行う
    # 1. DB問い合わせ: 送られてきたIDが、指定されたqueryset内に既に存在するか確認(論理削除も考慮)
    # 2. 自動エラー応答: 存在しない(または論理削除済み)IDだった場合、DRFは自動的に「400 Bad Request」を返す
    artist_ids = serializers.PrimaryKeyRelatedField(
        queryset=T_Artist.objects.filter(deleted_at__isnull=True),
        required=False,
        allow_null=True,
    )
    tracks = serializers.ListField(child=TrackRequestSerializer(), required=False, allow_null=True)
