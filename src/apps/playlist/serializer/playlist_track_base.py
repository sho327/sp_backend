from rest_framework import serializers

from apps.artist.serializer.artist_base import ArtistMiniResponseSerializer
from apps.playlist.models import T_PlaylistTrack


class PlaylistTrackBaseSerializer(serializers.ModelSerializer):
    """
    ベース定義：プレイリストトラック用。
    """

    class Meta:
        model = T_PlaylistTrack
        fields = "__all__"


class PlaylistTrackMiniResponseSerializer(PlaylistTrackBaseSerializer):
    """
    【最小構成】楽曲一覧用
    特定のリスト表示(アーティスト名と曲名だけ等)で使用。
    """

    # 外部キー先のIDだけではなく、名前だけは欲しい場合が多い
    artist_name = serializers.ReadOnlyField(source="artist.name")

    class Meta(PlaylistTrackBaseSerializer.Meta):
        # 画面に並べる最低限の項目に絞る
        fields = ["id", "name", "spotify_id", "artist_name"]


class PlaylistTrackFullResponseSerializer(PlaylistTrackBaseSerializer):
    """
    【トラック詳細構成】
    """

    # アーティスト情報をMini構成で展開
    artist = ArtistMiniResponseSerializer(read_only=True)

    class Meta(PlaylistTrackBaseSerializer.Meta):
        depth = 0
