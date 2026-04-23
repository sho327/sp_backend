from rest_framework import serializers


class ArtistSearchRequestSerializer(serializers.Serializer):
    """
    入力：フロントエンドから送られてくるデータの検品
    """

    q = serializers.CharField(
        required=True, allow_blank=False, max_length=255, help_text="検索キーワード"
    )
    limit = serializers.IntegerField(
        required=False, min_value=1, max_value=10, default=10
    )


class ArtistSearchResponseSerializer(serializers.Serializer):
    """
    出力：フロントエンドへ返すデータの定義
    """

    spotify_id = serializers.CharField()
    spotify_name = serializers.CharField()
    icon_url = serializers.URLField(allow_null=True)
    is_registered = serializers.BooleanField(default=False)
