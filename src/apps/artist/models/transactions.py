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
    # Deezer/ID
    deezer_id = models.CharField(
        db_column="deezer_id",
        verbose_name="Deezer/ID",
        db_comment="Deezer/ID",
        max_length=255,
    )
    # アーティスト名
    name = models.CharField(
        db_column="name",
        verbose_name="アーティスト名",
        db_comment="アーティスト名",
        max_length=255,
    )
    # Deezer画像(削除/物理削除の場合はCASCADE)
    deezer_image = models.ForeignKey(
        "common.T_FileResource",
        db_column="deezer_image_id",
        verbose_name="Deezer画像",
        db_comment="Deezer画像",
        on_delete=models.CASCADE,
        related_name="deezer_image_t_artist_set",
        null=True,
        blank=True,
    )
    # SetlistFm/MBID
    # 手動で設定された場合はこちらを優先。空の場合はname_enで自動検索する。
    setlistfm_mbid = models.CharField(
        db_column="setlistfm_mbid",
        verbose_name="SetlistFm/MBID",
        db_comment="setlistfm_mbid",
        max_length=100,
        null=True,
        blank=True,
    )
    # MBID/自動紐付けフラグ
    # 手動での紐づけの場合False、自動設定でMBIDを設定した場合はTrue
    is_mbid_autoset = models.BooleanField(
        db_column="is_mbid_autoset",
        verbose_name="MBID/自動紐付けフラグ",
        db_comment="MBID/自動紐付けフラグ",
        default=False,
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
                fields=["user", "deezer_id"],
                condition=Q(deleted_at__isnull=True),
                name="unique_t_artist_user_deezer_id_active",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.deezer_id})"
