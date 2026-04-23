from rest_framework import serializers

# --- アーティストモジュール ---
from apps.artist.models import M_ArtistContext, M_ArtistTag


class ArtistCreateRequestSerializer(serializers.Serializer):
    """
    入力：フロントエンドから送られてくるデータの検品
    """

    spotify_id = serializers.CharField(required=True)
    spotify_name = serializers.CharField(required=True)
    display_name = serializers.CharField(required=False, allow_null=True)
    icon_url = serializers.URLField(required=False, allow_null=True)

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
