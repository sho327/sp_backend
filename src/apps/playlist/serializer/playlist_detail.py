from rest_framework import serializers


class PlaylistDetailRequestSerializer(serializers.Serializer):
    """
    入力：フロントエンドから送られてくるデータの検品
    """

    # Spotify最新化フラグ
    refresh = serializers.BooleanField(required=False, default=False)
