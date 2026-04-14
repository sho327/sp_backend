from rest_framework import serializers
from apps.playlist.models import T_Playlist
from apps.artist.serializer.artist_base import ArtistMiniResponseSerializer
from apps.common.serializer.file_resource_base import FileResourceFullResponseSerializer
from apps.playlist.serializer.playlist_track_base import PlaylistTrackFullResponseSerializer

class PlaylistBaseSerializer(serializers.ModelSerializer):
    """
    ベース定義：モデルとの紐付けだけを行う。
    """
    class Meta:
        model = T_Playlist
        fields = '__all__'

class PlaylistMiniResponseSerializer(PlaylistBaseSerializer):
    """
    【最小構成】一覧用
    """
    # 外部キー対象のURLだけ取得させる
    # source='spotify_image.url' とすることで、
    # 階層を下げずに image_url というキーで直接文字列を返せる
    image_url = serializers.ReadOnlyField(source='image.url')

    class Meta(PlaylistBaseSerializer.Meta):
        fields = ['id', 'title', 'image_url', 'created_at']

class PlaylistFullResponseSerializer(PlaylistBaseSerializer):
    """
    【最大構成】詳細用
    """
    # 画像リソースの詳細を展開
    image = FileResourceFullResponseSerializer(read_only=True)
    
    # プレイリスト内のトラック(逆参照)を独自に定義
    tracks = serializers.SerializerMethodField()

    class Meta(PlaylistBaseSerializer.Meta):
        depth = 0

    def get_tracks(self, obj):
        """論理削除されていないトラックのみを詳細構成で返す"""
        active_tracks = obj.playlist_t_playlist_track_set.filter(deleted_at__isnull=True)
        return PlaylistTrackFullResponseSerializer(active_tracks, many=True).data
