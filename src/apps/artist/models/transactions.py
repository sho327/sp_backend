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
    # アーティスト名
    name = models.CharField(
        db_column="name",
        verbose_name="アーティスト名",
        db_comment="アーティスト名",
        max_length=255,
    )
    # Spotify画像(削除/物理削除の場合はCASCADE)
    spotify_image = models.ForeignKey(
        "common.T_FileResource",
        db_column="spotify_image_id",
        verbose_name="Spotify画像",
        db_comment="Spotify画像",
        on_delete=models.CASCADE,
        related_name="spotify_image_t_artist_set",
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
    # ジャンル
    genres = models.JSONField(
        db_column="genres",
        verbose_name="ジャンル",
        db_comment="ジャンル",
        default=list,
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
                name="unique_t_artist_user_sporify_id_active",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.spotify_id})"
