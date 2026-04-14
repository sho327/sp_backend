from rest_framework import serializers

# --- アーティストモジュール ---
from apps.artist.models import T_Artist


class PlaylistGenerateRequestSerializer(serializers.Serializer):
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
    pattern = serializers.ChoiceField(
        choices=["top_tracks", "set_list", "moodfilter"],
        default="top_tracks",
    )
    get_tracks_count = serializers.IntegerField(
        min_value=1,
        max_value=20,
        default=5,
    )
    mood_brightness = serializers.IntegerField(min_value=0, max_value=100, default=50)
    mood_intensity = serializers.IntegerField(min_value=0, max_value=100, default=50)
    related_artists_count = serializers.IntegerField(
        min_value=0,
        max_value=5,
        default=0,
    )
