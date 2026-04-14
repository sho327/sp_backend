import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q, UniqueConstraint
from simple_history.models import HistoricalRecords

# --- コアモジュール ---
from core.models import BaseModel


# アーティストタグマスタ
class M_ArtistTag(BaseModel):
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
    # タグ名
    name = models.CharField(
        db_column="name",
        verbose_name="タグ名",
        db_comment="タグ名",
        max_length=64,
    )

    # django-simple-historyを使用
    # history = HistoricalRecords()

    # テーブル名
    class Meta:
        db_table = "m_artist_tag"
        db_table_comment = "アーティストタグマスタ"
        verbose_name = "アーティストタグマスタ"
        verbose_name_plural = "アーティストタグマスタ"
        constraints = [
            # 未削除のレコード内でのみ、タグ名が重複しないことを保証
            UniqueConstraint(
                fields=["name"],
                condition=Q(deleted_at__isnull=True),
                name="unique_m_artist_tag_name_active",
            ),
        ]

    def __str__(self):
        return f"{self.name}"


# アーティストコンテキストマスタ
class M_ArtistContext(BaseModel):
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
    # コンテキスト名
    name = models.CharField(
        db_column="name",
        verbose_name="コンテキスト名",
        db_comment="コンテキスト名",
        max_length=64,
    )

    # django-simple-historyを使用
    # history = HistoricalRecords()

    # テーブル名
    class Meta:
        db_table = "m_artist_context"
        db_table_comment = "アーティストコンテキストマスタ"
        verbose_name = "アーティストコンテキストマスタ"
        verbose_name_plural = "アーティストコンテキストマスタ"
        constraints = [
            # 未削除のレコード内でのみ、コンテキスト名が重複しないことを保証
            UniqueConstraint(
                fields=["name"],
                condition=Q(deleted_at__isnull=True),
                name="unique_m_artist_context_name_active",
            ),
        ]

    def __str__(self):
        return f"{self.name}"
