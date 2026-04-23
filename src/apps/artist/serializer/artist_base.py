from rest_framework import serializers

from apps.artist.models import T_Artist
from apps.artist.serializer.master_artist_context_base import (
    MasterArtistContextMiniResponseSerializer,
)
from apps.artist.serializer.master_artist_tag_base import (
    MasterArtistTagMiniResponseSerializer,
)
from apps.common.serializer.file_resource_base import FileResourceMiniResponseSerializer


class ArtistBaseSerializer(serializers.ModelSerializer):
    """
    ベース定義：モデルとの紐付けだけを行う。
    直接は使わず、継承して利用する。
    """

    class Meta:
        model = T_Artist
        fields = "__all__"  # 基本は全フィールド対象


class ArtistMiniResponseSerializer(ArtistBaseSerializer):
    """
    【最小構成】一覧用
    一覧で必要な項目(画像URLなど)だけを抽出。
    """

    # 外部キー対象のURLだけ取得させる
    # source='external_icon.url' とすることで、
    # 階層を下げずに icon_url というキーで直接文字列を返せる
    icon_url = serializers.ReadOnlyField(source="external_icon.url")
    tags = MasterArtistTagMiniResponseSerializer(many=True, read_only=True)

    class Meta(ArtistBaseSerializer.Meta):
        fields = [
            "id",
            "spotify_id",
            "spotify_name",
            "display_name",
            "deezer_id",
            "is_deezer_autoset",
            "lastfm_name",
            "mbid",
            "is_mbid_autoset",
            "icon_url",
            "tags",
            "sync_at",
        ]


class ArtistFullResponseSerializer(ArtistBaseSerializer):
    """
    【最大構成】詳細用
    基本モデルの全フィールド。
    ただし、外部キー先のIDだけでなく中身(オブジェクト)を返したい項目だけ上書き。
    """

    # Mini系のシリアライザを再利用し中身を展開
    context = MasterArtistContextMiniResponseSerializer(read_only=True)
    tags = MasterArtistTagMiniResponseSerializer(many=True, read_only=True)
    external_icon = FileResourceMiniResponseSerializer(read_only=True)

    class Meta(ArtistBaseSerializer.Meta):
        # Baseの fields = '__all__' を継承。
        # 上記で定義したcontextやtagsは自動的にこの「__all__」の中で差し替わる。
        depth = 0  # 勝手な展開を防ぐため0を推奨。展開は上記のように明示的に書く。
