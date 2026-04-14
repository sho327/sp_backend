from rest_framework import serializers

# --- プレイリストモジュール ---
from apps.playlist.models import T_Playlist
from apps.playlist.serializer.ms_t_playlist_track import MS_PlaylistTrackSerializer

class MS_PlaylistSerializer(serializers.ModelSerializer):
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
        return MS_PlaylistTrackSerializer(qs, many=True).data

    def get_track_count(self, obj):
        return obj.playlist_t_playlist_track_set.filter(deleted_at__isnull=True).count()
