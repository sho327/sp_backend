from rest_framework import serializers

# --- プレイリストモジュール ---
from apps.playlist.models import T_PlaylistTrack

class MS_PlaylistTrackSerializer(serializers.ModelSerializer):
    """プレイリスト明細行。"""

    class Meta:
        model = T_PlaylistTrack
        fields = (
            "id",
            "name",
            "spotify_id",
            "created_at",
        )
