from rest_framework import serializers

from apps.playlist.models import T_Playlist, T_PlaylistTrack


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
    popular_tracks_count = serializers.IntegerField(min_value=1, max_value=20, default=5)
    total_tracks = serializers.IntegerField(min_value=5, max_value=100, default=30)
    pattern = serializers.ChoiceField(
        choices=["balanced", "live_focus", "popular_focus"],
        default="balanced",
    )


class ReplaceTracksSerializer(serializers.Serializer):
    """既存プレイリストの曲差し替え入力。"""

    track_ids = serializers.ListField(
        child=serializers.CharField(max_length=255),
        allow_empty=False,
    )


class SearchTracksSerializer(serializers.Serializer):
    """アーティスト指定のトラック検索入力。"""

    artist_spotify_id = serializers.CharField(max_length=255)
    q = serializers.CharField(max_length=255)
    limit = serializers.IntegerField(min_value=1, max_value=50, default=20)


class PlaylistTrackSerializer(serializers.ModelSerializer):
    """プレイリスト明細行。"""

    class Meta:
        model = T_PlaylistTrack
        fields = ("id", "name", "spotify_id", "preview_url", "created_at")


class PlaylistSerializer(serializers.ModelSerializer):
    """プレイリスト詳細。履歴一覧/詳細で共通利用。"""

    tracks = serializers.SerializerMethodField()
    track_count = serializers.SerializerMethodField()

    class Meta:
        model = T_Playlist
        fields = (
            "id",
            "title",
            "spotify_id",
            "image",
            "artists",
            "track_count",
            "tracks",
            "created_at",
            "updated_at",
        )

    def get_tracks(self, obj):
        # 一覧性を優先し、作成順で返却する
        qs = obj.playlist_t_playlist_track_set.filter(deleted_at__isnull=True).order_by(
            "created_at"
        )
        return PlaylistTrackSerializer(qs, many=True).data

    def get_track_count(self, obj):
        return obj.playlist_t_playlist_track_set.filter(deleted_at__isnull=True).count()
