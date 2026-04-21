from rest_framework import serializers
from django.db.models import Sum

from apps.common.serializer.file_resource_base import FileResourceMiniResponseSerializer

# --- プレイリストモジュール ---
from apps.playlist.models import T_Playlist
from apps.playlist.serializer.playlist_track_base import PlaylistTrackMiniResponseSerializer


class PlaylistBaseSerializer(serializers.ModelSerializer):
    """
    ベース定義：モデルとの紐付けだけを行う。
    """

    class Meta:
        model = T_Playlist
        fields = "__all__"


class PlaylistMiniResponseSerializer(PlaylistBaseSerializer):
    """
    【最小構成】一覧用
    """

    # 外部キー対象のURLだけ取得させる
    # source='spotify_image.url' とすることで、
    # 階層を下げずに image_url というキーで直接文字列を返せる
    image_url = serializers.SerializerMethodField() # 一覧取得のプレイリスト毎に実行される(N+1問題)/サービス側でselect_related("image")は必須

    # 2026/4/19 シリアライザで計算するとプレイリストの数だけ毎回集計クエリが走り重くなる
    # ReadOnlyFieldにし、サービス側でannotateで設定するようにする
    # 合計時間のフィールド
    # total_duration_ms = serializers.SerializerMethodField()
    total_spotify_duration_ms = serializers.ReadOnlyField() # 一覧や詳細サービス側でannotateで付与する想定で追加する
    # 2026/4/19 シリアライザで計算するとプレイリストの数だけ毎回集計クエリが走り重くなる

    class Meta(PlaylistBaseSerializer.Meta):
        fields = [
            "id", 
            "title", 
            "image_url", 
            "created_at",
            "total_spotify_duration_ms",
        ]
    
    def get_image_url(self, obj):
        """
        ForeignKey(image)が存在する場合のみ、T_FileResourceの@property urlを呼び出す
        """
        if obj.image:
            return obj.image.url
        return None
    
    # 2026/4/19 シリアライザで計算するとプレイリストの数だけ毎回集計クエリが走り重くなる
    # def get_total_duration_ms(self, obj):
    #     """トラックの duration_ms を合計して返す"""
    #     total = obj.playlist_t_playlist_track_set.filter(
    #         deleted_at__isnull=True
    #     ).aggregate(Sum('duration_ms'))['duration_ms__sum']
        
    #     return total or 0  # データが空なら0を返す
    # 2026/4/19 シリアライザで計算するとプレイリストの数だけ毎回集計クエリが走り重くなる


class PlaylistFullResponseSerializer(PlaylistBaseSerializer):
    """
    【最大構成】詳細用
    """

    # 画像リソースの詳細を展開
    image = FileResourceMiniResponseSerializer(read_only=True)

    # プレイリスト内のトラック(逆参照)を独自に定義
    tracks = serializers.SerializerMethodField()
    
    # 2026/4/19 シリアライザで計算するとプレイリストの数だけ毎回集計クエリが走り重くなる
    # ReadOnlyFieldにし、サービス側でannotateで設定するようにする
    # 合計時間のフィールド
    # total_duration_ms = serializers.SerializerMethodField()
    total_spotify_duration_ms = serializers.ReadOnlyField()
    # 2026/4/19 シリアライザで計算するとプレイリストの数だけ毎回集計クエリが走り重くなる

    class Meta(PlaylistBaseSerializer.Meta):
        # depth = 0 # デフォルト値
        fields = [
            "id", 
            "title", 
            "image", 
            "tracks", 
            "total_spotify_duration_ms",
        ]

    def get_tracks(self, obj):
        """論理削除されていないトラックのみを詳細構成で返す"""
        active_tracks = obj.playlist_t_playlist_track_set.filter(
            deleted_at__isnull=True
        )
        return PlaylistTrackMiniResponseSerializer(
            active_tracks, many=True
        ).data
    
    # 2026/4/19 シリアライザで計算するとプレイリストの数だけ毎回集計クエリが走り重くなる
    # def get_total_duration_ms(self, obj):
    #     """トラックの duration_ms を合計して返す"""
    #     total = obj.playlist_t_playlist_track_set.filter(
    #         deleted_at__isnull=True
    #     ).aggregate(Sum('duration_ms'))['duration_ms__sum']
        
    #     return total or 0  # データが空なら0を返す
    # 2026/4/19 シリアライザで計算するとプレイリストの数だけ毎回集計クエリが走り重くなる
