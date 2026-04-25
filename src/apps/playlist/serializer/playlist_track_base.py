from rest_framework import serializers

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

    class Meta(PlaylistTrackBaseSerializer.Meta):
        # 画面に並べる最低限の項目に絞る
        fields = [
            "id", 
            "spotify_id", 
            "spotify_name", 
            "spotify_artist_name",
            "spotify_duration_ms",
        ]


class PlaylistTrackFullResponseSerializer(PlaylistTrackBaseSerializer):
    """
    【最大構成】詳細用
    Baseの定義（__all__）をそのまま使い、モデルの変更に自動追従させる
    """
    pass


class CustomPlaylistTrackRequestSerializer(serializers.Serializer):
    """
    入力：生成された楽曲データを使用したプレイリスト生成/追加用(共通化の為にbase側で定義)
    """

    spotify_id = serializers.CharField()
    spotify_name = serializers.CharField()
    spotify_isrc = serializers.CharField(allow_null=True, required=False)
    spotify_artist_id = serializers.CharField()
    spotify_artist_name = serializers.CharField()
    display_artist_name = serializers.CharField(allow_null=True, required=False)
    spotify_popularity = serializers.IntegerField(
        min_value=0, 
        max_value=100,
        default=0
    )
    spotify_duration_ms = serializers.IntegerField(allow_null=True, required=False)
    spotify_album_type = serializers.CharField(allow_null=True, required=False)
    spotify_album_id = serializers.CharField(allow_null=True, required=False)
    spotify_album_name = serializers.CharField(allow_null=True, required=False)
    spotify_release_date = serializers.CharField(allow_null=True, required=False)

class CustomPlaylistTrackResponseSerializer(serializers.Serializer):
    """
    出力：生成された楽曲データの返却用(共通化の為にbase側で定義)
    """

    spotify_id = serializers.CharField()
    spotify_name = serializers.CharField()
    spotify_isrc = serializers.CharField(allow_null=True)
    spotify_artist_name = serializers.CharField()
    display_artist_name = serializers.CharField(allow_null=True)
    spotify_popularity = serializers.IntegerField()
    spotify_duration_ms = serializers.IntegerField(allow_null=True)
    spotify_album_type = serializers.CharField(allow_null=True)
    spotify_album_id = serializers.CharField(allow_null=True)
    spotify_album_name = serializers.CharField(allow_null=True)
    spotify_release_date = serializers.CharField(allow_null=True)
