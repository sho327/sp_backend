import uuid

from django.db import models
from django.db.models import Q, UniqueConstraint
from simple_history.models import HistoricalRecords

# --- コアモジュール ---
from core.models import BaseModel


# アーティストトラン
class T_Artist(BaseModel):
    """登録したアーティストの情報(名称や画像はSpotifyより取得)"""

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
        "account.M_User",  # 循環参照対策(文字で定義することで、後での紐付けとする)
        db_column="user_id",
        verbose_name="ユーザ",
        db_comment="ユーザ",
        on_delete=models.CASCADE,
        # 逆参照名を定義(例: 「参照先インスタンス.[related_name]」/通常参照は「本インスタンス.参照先モデル名(_id)」で取得可能)
        related_name="user_t_artist_set",  # 役割_[複数形]ルール
    )
    # Spotify/ID
    spotify_id = models.CharField(
        db_column="spotify_id",
        verbose_name="Spotify/ID",
        db_comment="Spotify/ID",
        max_length=255,
    )
    # Spotify/アーティスト名
    spotify_name = models.CharField(
        db_column="spotify_name",
        verbose_name="Spotify/アーティスト名",
        db_comment="Spotify/アーティスト名",
        max_length=255,
    )
    # アーティスト表示名
    display_name = models.CharField(
        db_column="display_name",
        verbose_name="アーティスト表示名",
        db_comment="アーティスト表示名",
        max_length=255,
        null=True,
        blank=True,
    )
    # 外部アイコン(削除/物理削除の場合はCASCADE)
    external_icon = models.ForeignKey(
        "common.T_FileResource",
        db_column="external_icon_id",
        verbose_name="外部アイコン",
        db_comment="外部アイコン",
        on_delete=models.CASCADE,
        related_name="external_icon_t_artist_set",
        null=True,
        blank=True,
    )
    # コンテキスト/きっかけ(削除/物理削除の場合はSET_NULL)
    context = models.ForeignKey(
        "artist.M_ArtistContext",  # 循環参照対策(文字で定義することで、後での紐付けとする)
        db_column="context",
        verbose_name="コンテキスト",
        db_comment="コンテキスト",
        on_delete=models.SET_NULL,
        # 逆参照名を定義(例: 「参照先インスタンス.[related_name]」/通常参照は「本インスタンス.参照先モデル名(_id)」で取得可能)
        related_name="context_t_artist_set",
        null=True,
        blank=True,
    )
    # タグ
    tags = models.ManyToManyField(
        "artist.M_ArtistTag",  # 循環参照対策(文字で定義することで、後での紐付けとする)
        # ManyToManyFieldにはdb_columnは通常指定しない（中間テーブルで制御）
        verbose_name="タグ",
        db_comment="タグ",
        through="artist.R_ArtistTag",  # 循環参照対策(文字で定義することで、後での紐付けとする)
        # 逆参照名を定義(例: 「参照先インスタンス.[related_name]」/通常参照は「本インスタンス.参照先モデル名(_id)」で取得可能)
        related_name="tags_t_artist_set",
    )
    # -------------------------------------
    # その他メタ情報
    # -------------------------------------
    # Deezer/ID
    deezer_id = models.CharField(
        db_column="deezer_id",
        verbose_name="Deezer/ID",
        db_comment="Deezer/ID",
        max_length=255,
        null=True,
        blank=True,
    )
    # Deezer/自動紐付けフラグ
    is_deezer_autoset = models.BooleanField(
        db_column="is_deezer_autoset",
        verbose_name="Deezer/自動紐付けフラグ",
        db_comment="Deezer/自動紐付けフラグ",
        default=False,
    )
    # LastFM/アーティスト名
    lastfm_name = models.CharField(
        db_column="lastfm_name",
        verbose_name="LastFM/アーティスト名",
        db_comment="LastFM/アーティスト名",
        max_length=255,
        null=True,
        blank=True,
    )
    # MBID
    mbid = models.CharField(
        db_column="mbid",
        verbose_name="MBID",
        db_comment="MBID",
        max_length=100,
        null=True,
        blank=True,
    )
    # MBID/自動紐付けフラグ
    is_mbid_autoset = models.BooleanField(
        db_column="is_mbid_autoset",
        verbose_name="MBID/自動紐付けフラグ",
        db_comment="MBID/自動紐付けフラグ",
        default=False,
    )
    # 同期日時
    sync_at = models.DateTimeField(
        db_column="sync_at",
        verbose_name="同期日時",
        db_comment="同期日時",
        null=True,
        blank=True,
    )

    # django-simple-historyを使用
    # history = HistoricalRecords()

    # テーブル名
    class Meta:
        db_table = "t_artist"
        db_table_comment = "アーティストトラン"
        verbose_name = "アーティストトラン"
        verbose_name_plural = "アーティストトラン"
        constraints = [
            # 同一ユーザ内に同一アーティストが重複して登録されるのを防ぐ（論理削除考慮）
            UniqueConstraint(
                fields=["user", "spotify_id"],
                condition=Q(deleted_at__isnull=True),
                name="unique_t_artist_user_spotify_id_active",
            ),
        ]

    def __str__(self):
        return f"{self.spotify_name} ({self.spotify_id}/{self.deezer_id})"
