from rest_framework import serializers

class SearchTracksSerializer(serializers.Serializer):
    """アーティスト指定のトラック検索入力。"""

    artist_spotify_id = serializers.CharField(max_length=255)
    q = serializers.CharField(max_length=255)
    limit = serializers.IntegerField(min_value=1, max_value=50, default=20)
