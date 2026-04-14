from rest_framework import serializers

class PlaylistListRequestSerializer(serializers.Serializer):
    """
    入力：フロントエンドから送られてくるデータの検品
    """
    title = serializers.CharField(required=False, allow_blank=True, max_length=255)
    # ページング
    page = serializers.IntegerField(required=False, min_value=1, default=1)
    per_page = serializers.IntegerField(required=False, min_value=1, max_value=100, default=20)
