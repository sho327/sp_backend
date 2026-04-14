from django.db import models
from django.db.models import Q, UniqueConstraint
from simple_history.models import HistoricalRecords

# --- コアモジュール ---
from core.models import BaseModel


# プレイリストアーティストリレーション
class R_PlaylistArtist(BaseModel):
    """ プレイリストトラン/アーティストトランの紐づけ """
    # ---------- Consts ----------
    # ---------- Fields ----------
    # ID (BIGINT PRIMARY KEY) はDjangoが自動で付与
    # プレイリスト(削除/物理削除の場合はCASCADE)
    playlist = models.ForeignKey(
        "playlist.T_Playlist",  # 循環参照対策(文字で定義することで、後での紐付けとする)
        db_column="playlist_id",
        verbose_name="プレイリスト",
        db_comment="プレイリスト",
        on_delete=models.CASCADE,
        # 逆参照名を定義(例: 「参照先インスタンス.[related_name]」/通常参照は「本インスタンス.参照先モデル名(_id)」で取得可能)
        related_name="playlist_r_playlist_artist_set",
    )
    # アーティスト(削除/物理削除の場合はCASCADE)
    artist = models.ForeignKey(
        "artist.T_Artist",  # 循環参照対策(文字で定義することで、後での紐付けとする)
        db_column="artist_id",
        verbose_name="アーティスト",
        db_comment="アーティスト",
        on_delete=models.CASCADE,
        # 逆参照名を定義(例: 「参照先インスタンス.[related_name]」/通常参照は「本インスタンス.参照先モデル名(_id)」で取得可能)
        related_name="artist_r_playlist_artist_set",
    )

    # django-simple-historyを使用
    # history = HistoricalRecords()

    # テーブル名
    class Meta:
        db_table = "r_playlist_artist"
        db_table_comment = "プレイリストアーティストリレーション"
        verbose_name = "プレイリストアーティストリレーション"
        verbose_name_plural = "プレイリストアーティストリレーション"
        constraints = [
            # 同一アーティスト内に同一タグが重複して登録されるのを防ぐ（論理削除考慮）
            UniqueConstraint(
                fields=["playlist", "artist"],
                condition=Q(deleted_at__isnull=True),
                name="unique_r_playlist_artist_playlist_artist_active",
            ),
        ]

    def __str__(self):
        return f"{self.playlist} - {self.artist}"

