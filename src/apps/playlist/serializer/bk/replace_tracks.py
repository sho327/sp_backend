from rest_framework import serializers

class ReplaceTracksSerializer(serializers.Serializer):
    """既存プレイリストの曲差し替え入力。"""

    track_ids = serializers.ListField(
        child=serializers.CharField(max_length=255),
        allow_empty=False,
    )
