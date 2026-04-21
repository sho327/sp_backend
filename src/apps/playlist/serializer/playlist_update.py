from rest_framework import serializers

# --- アーティストモジュール ---
from apps.artist.models import T_Artist

# --- プレイリストモジュール ---
from apps.playlist.serializer.playlist_track_base import CustomPlaylistTrackRequestSerializer

class PlaylistUpdateRequestSerializer(serializers.Serializer):
    """
    入力：フロントエンドから送られてくるデータの検品
    ※バイナリ画像を扱うため、Multipartリクエスト専用
    """
    def __init__(self, *args, **kwargs):
        # コンテキストからuserを取得してquerysetを絞り込む
        user = kwargs.get('context', {}).get('request').user
        super().__init__(*args, **kwargs)
        if user:
            self.fields['artist_ids'].queryset = T_Artist.objects.filter(
                user=user, deleted_at__isnull=True
            )

    title = serializers.CharField(required=True)
    image = serializers.ImageField(required=False, allow_null=True)
    
    # formDataとして1テキスト内にJson形式で格納されるため、JSONFieldで受け取り、各種validate側で個別検証を行う
    artist_ids = serializers.JSONField(required=False, allow_null=True)
    tracks = serializers.JSONField(required=False, allow_null=True)

    def validate_artist_ids(self, value):
        """artist_idsを手動で検証・取得する"""
        if not value:
            return []
        
        # valueはJSONFieldにより既にリスト化されているはず
        if not isinstance(value, list):
            raise serializers.ValidationError("artist_idsはリスト形式である必要があります。")

        user = self.context['request'].user
        # IDリストから有効なアーティストを取得
        artists = T_Artist.objects.filter(
            id__in=value, 
            user=user, 
            deleted_at__isnull=True
        )
        return list(artists)
    
    def validate_tracks(self, value):
        """JSONFieldとして受け取ったデータを、個別のシリアライザでバリデーションする"""
        if not value:
            return []
        
        # value は既にjson.loadsされた状態のリスト(辞書)
        if not isinstance(value, list):
            raise serializers.ValidationError("tracksはリスト形式である必要があります。")

        # 個別のトラックデータをCustomPlaylistTrackRequestSerializerで検証
        validated_tracks = []
        for track_data in value:
            track_serializer = CustomPlaylistTrackRequestSerializer(data=track_data)
            if track_serializer.is_valid(raise_exception=True):
                validated_tracks.append(track_serializer.validated_data)
        
        return validated_tracks
