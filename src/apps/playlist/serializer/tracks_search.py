from rest_framework import serializers

class TracksSearchRequestSerializer(serializers.Serializer):
    """
    入力：フロントエンドから送られてくるデータの検品
    """
    
    search_artist_name = serializers.CharField(max_length=255, required=False, allow_null=True, allow_blank=True)
    search_track_name = serializers.CharField(max_length=255, required=False, allow_null=True, allow_blank=True)
    limit = serializers.IntegerField(min_value=1, max_value=10, default=1)
