from django.db import models
from django.db.models import Q, UniqueConstraint
from simple_history.models import HistoricalRecords

# --- コアモジュール ---
from core.models import BaseModel


# アーティストタグリレーション
class R_ArtistTag(BaseModel):
    """アーティストトラン/アーティストタグマスタの紐づけ"""

    # ---------- Consts ----------
    # ---------- Fields ----------
    # ID (BIGINT PRIMARY KEY) はDjangoが自動で付与
    # アーティスト(削除/物理削除の場合はCASCADE)
    artist = models.ForeignKey(
        "artist.T_Artist",  # 循環参照対策(文字で定義することで、後での紐付けとする)
        db_column="artist_id",
        verbose_name="アーティスト",
        db_comment="アーティスト",
        on_delete=models.CASCADE,
        # 逆参照名を定義(例: 「参照先インスタンス.[related_name]」/通常参照は「本インスタンス.参照先モデル名(_id)」で取得可能)
        related_name="artist_r_artist_tag_set",
    )
    # タグ(削除/物理削除の場合はCASCADE)
    tag = models.ForeignKey(
        "artist.M_ArtistTag",  # 循環参照対策(文字で定義することで、後での紐付けとする)
        db_column="tag_id",
        verbose_name="タグ",
        db_comment="タグ",
        on_delete=models.CASCADE,
        # 逆参照名を定義(例: 「参照先インスタンス.[related_name]」/通常参照は「本インスタンス.参照先モデル名(_id)」で取得可能)
        related_name="tag_r_artist_tag_set",
    )

    # django-simple-historyを使用
    # history = HistoricalRecords()

    # テーブル名
    class Meta:
        db_table = "r_artist_tag"
        db_table_comment = "アーティストタグリレーション"
        verbose_name = "アーティストタグリレーション"
        verbose_name_plural = "アーティストタグリレーション"
        constraints = [
            # 同一アーティスト内に同一タグが重複して登録されるのを防ぐ（論理削除考慮）
            UniqueConstraint(
                fields=["artist", "tag"],
                condition=Q(deleted_at__isnull=True),
                name="unique_r_artist_tag_artist_tag_active",
            ),
        ]

    def __str__(self):
        return f"{self.artist} - {self.tag}"
