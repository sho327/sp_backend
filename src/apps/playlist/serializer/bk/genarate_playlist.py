from rest_framework import serializers

class GeneratePlaylistSerializer(serializers.Serializer):
    """プレイリスト生成時の入力。"""

    # 保存時に使用する基本情報
    title = serializers.CharField(max_length=255)
    image_id = serializers.UUIDField(required=False, allow_null=True)

    # 生成パラメータ
    artist_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False,
    )
    use_recent_setlist = serializers.BooleanField(default=True)
    mood_brightness = serializers.IntegerField(min_value=0, max_value=100, default=50)
    mood_intensity = serializers.IntegerField(min_value=0, max_value=100, default=50)
    popular_tracks_count = serializers.IntegerField(
        min_value=1, max_value=20, default=5
    )
    total_tracks = serializers.IntegerField(min_value=5, max_value=100, default=30)
    pattern = serializers.ChoiceField(
        choices=["balanced", "live_focus", "popular_focus"],
        default="balanced",
    )
