from rest_framework import serializers

class ArtistSearchRequestSerializer(serializers.Serializer):
    """
    入力：フロントエンドから送られてくるデータの検品
    """
    q = serializers.CharField(
        required=True, 
        allow_blank=False, 
        max_length=255, 
        help_text="検索キーワード"
    )
    limit = serializers.IntegerField(
        required=False, 
        min_value=1, 
        max_value=50, 
        default=20
    )

class ArtistSearchResponseSerializer(serializers.Serializer):
    """
    出力：フロントエンドへ返すデータの定義
    """
    spotify_id = serializers.CharField()
    name = serializers.CharField()
    image_url = serializers.URLField(allow_null=True)
    genres = serializers.ListField(child=serializers.CharField())
    popularity = serializers.IntegerField()
    is_registered = serializers.BooleanField(default=False)
