import uuid

from django.db import models
from django.db.models import Q, UniqueConstraint

from core.models import BaseModel


# プレイリストトラン
class T_Playlist(BaseModel):
    """ユーザーが作成したプレイリストの管理"""

    # ---------- Consts ----------
    # ---------- Fields ----------
    # ID(URLに使用される可能性もあるため、予測できないUUIDで保持する)
    id = models.UUIDField(
        db_column="id",
        verbose_name="ID",
        db_comment="ID",
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    # ユーザ(削除/物理削除の場合はCASCADE)
    user = models.ForeignKey(
        "account.T_Profile",  # 循環参照対策(文字で定義することで、後での紐付けとする)
        db_column="user_id",
        verbose_name="ユーザ",
        db_comment="ユーザ",
        on_delete=models.CASCADE,
        # 逆参照名を定義(例: 「参照先インスタンス.[related_name]」/通常参照は「本インスタンス.参照先モデル名(_id)」で取得可能)
        related_name="user_t_playlist_set",  # 役割_[複数形]ルール
    )
    # タイトル
    title = models.CharField(
        db_column="title",
        verbose_name="タイトル",
        db_comment="タイトル",
        max_length=255,
    )
    # 画像(任意)
    image = models.ForeignKey(
        "common.T_FileResource",
        db_column="image_id",
        verbose_name="画像",
        db_comment="画像",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="image_t_playlist_set",
    )
    # アーティスト
    artists = models.ManyToManyField(
        "artist.T_Artist",  # 循環参照対策(文字で定義することで、後での紐付けとする)
        verbose_name="アーティスト",
        db_comment="アーティスト",
        # 逆参照名を定義(例: 「参照先インスタンス.[related_name]」/通常参照は「本インスタンス.参照先モデル名(_id)」で取得可能)
        related_name="artists_t_playlist_set",
    )
    # Spotify/ID
    spotify_id = models.CharField(
        db_column="spotify_id",
        verbose_name="Spotify/ID",
        db_comment="Spotify/ID",
        max_length=255,
        blank=True,
        null=True,
    )

    # django-simple-historyを使用
    # history = HistoricalRecords()

    # テーブル名
    class Meta:
        db_table = "t_playlist"
        db_table_comment = "プレイリストトラン"
        verbose_name = "プレイリストトラン"
        verbose_name_plural = "プレイリストトラン"
        constraints = [
            # 同一ユーザ内に同一アーティストが重複して登録されるのを防ぐ（論理削除考慮）
            UniqueConstraint(
                fields=["user", "spotify_id"],
                condition=Q(deleted_at__isnull=True),
                name="unique_t_playlist_user_spotify_id_active",
            ),
        ]

    def __str__(self):
        return f"{self.spotify_id}"


# プレイリストトラックトラン
class T_PlaylistTrack(BaseModel):
    """ユーザーが作成したプレイリストの管理"""

    # ---------- Consts ----------
    # ---------- Fields ----------
    # ID(URLに使用される可能性もあるため、予測できないUUIDで保持する)
    id = models.UUIDField(
        db_column="id",
        verbose_name="ID",
        db_comment="ID",
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    # プレイリスト(削除/物理削除の場合はCASCADE)
    playlist = models.ForeignKey(
        "playlist.T_Playlist",
        db_column="playlist_id",
        verbose_name="プレイリスト",
        db_comment="プレイリスト",
        on_delete=models.CASCADE,
        related_name="playlist_t_playlist_track_set",
    )
    # トラック名
    name = models.CharField(
        db_column="name",
        verbose_name="トラック名",
        db_comment="トラック名",
        max_length=255,
    )
    # アーティスト(任意)
    artist = models.ForeignKey(
        "artist.T_Artist",  # 循環参照対策(文字で定義することで、後での紐付けとする)
        db_column="artist_id",
        verbose_name="アーティスト",
        db_comment="アーティスト",
        on_delete=models.SET_NULL,
        related_name="artist_track_t_playlist_track_set",
        null=True,
        blank=True,
    )
    # プレビューURL
    preview_url = models.URLField(
        db_column="preview_url",
        verbose_name="プレビューURL",
        db_comment="プレビューURL",
        blank=True,
        null=True,
    )
    # Spotify/ID
    spotify_id = models.CharField(
        db_column="spotify_id",
        verbose_name="Spotify/ID",
        db_comment="Spotify/ID",
        max_length=255,
        blank=True,
        null=True,
    )

    # django-simple-historyを使用
    # history = HistoricalRecords()

    # テーブル名
    class Meta:
        db_table = "t_playlist_track"
        db_table_comment = "プレイリストトラックトラン"
        verbose_name = "プレイリストトラックトラン"
        verbose_name_plural = "プレイリストトラックトラン"
        constraints = [
            # 同一プレイリスト内で同一Spotify IDが重複しないようにする（論理削除考慮）
            UniqueConstraint(
                fields=["playlist", "spotify_id"],
                condition=Q(deleted_at__isnull=True),
                name="unique_t_playlist_track_playlist_spotify_id_active",
            ),
        ]

    def __str__(self):
        return f"{self.spotify_id}"
