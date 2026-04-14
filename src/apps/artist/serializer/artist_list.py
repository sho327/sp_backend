from rest_framework import serializers

class ArtistListRequestSerializer(serializers.Serializer):
    """
    入力：フロントエンドから送られてくるデータの検品
    """
    name = serializers.CharField(required=False, allow_blank=True, max_length=255)
    # 複数IDを受け取るためのListField。子要素をUUIDFieldにすることで形式チェックも自動化
    tag_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        help_text="タグIDのリスト"
    )
    # ページング
    page = serializers.IntegerField(required=False, min_value=1, default=1)
    per_page = serializers.IntegerField(required=False, min_value=1, max_value=100, default=20)
    # Spotify最新化フラグ
    refresh = serializers.BooleanField(required=False, default=False)
