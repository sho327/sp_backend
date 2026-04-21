import uuid

from django.db import models
from django.db.models import Q, UniqueConstraint
from django.core.validators import MaxValueValidator, MinValueValidator

# --- 共通モジュール ---
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
        "account.M_User",  # 循環参照対策(文字で定義することで、後での紐付けとする)
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
    # アーティスト(プレイリスト作成時のアーティスト登録情報)
    artists = models.ManyToManyField(
        "artist.T_Artist",  # 循環参照対策(文字で定義することで、後での紐付けとする)
        verbose_name="アーティスト",
        db_comment="アーティスト",
        through="playlist.R_PlaylistArtist",  # 循環参照対策(文字で定義することで、後での紐付けとする)
        # 逆参照名を定義(例: 「参照先インスタンス.[related_name]」/通常参照は「本インスタンス.参照先モデル名(_id)」で取得可能)
        related_name="artists_t_playlist_set",
    )

    # django-simple-historyを使用
    # history = HistoricalRecords()

    # テーブル名
    class Meta:
        db_table = "t_playlist"
        db_table_comment = "プレイリストトラン"
        verbose_name = "プレイリストトラン"
        verbose_name_plural = "プレイリストトラン"

    def __str__(self):
        return f"{self.title}"


# プレイリストトラックトラン
class T_PlaylistTrack(BaseModel):
    """ユーザーが作成したプレイリストの管理"""

    # ---------- Consts ----------
    class AlbumType(models.TextChoices):
        ALBUM = "album", "Album"
        SINGLE = "single", "Single"
        COMPILATION = "compilation", "Compilation"
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
    # Spotify/ID
    spotify_id = models.CharField(
        db_column="spotify_id",
        verbose_name="Spotify/ID",
        db_comment="Spotify/ID",
        max_length=255,
    )
    # Spotifyトラック名
    spotify_name = models.CharField(
        db_column="spotify_name",
        verbose_name="Spotifyトラック名",
        db_comment="Spotifyトラック名",
        max_length=255,
    )
    # Spotify/ISRC
    spotify_isrc = models.CharField(
        db_column="spotify_isrc",
        verbose_name="Spotify/ISRC",
        db_comment="Spotify/ISRC",
        max_length=12,
    )
    # Spotifyアーティスト名
    spotify_artist_name = models.CharField(
        db_column="spotify_artist_name",
        verbose_name="Spotifyアーティスト名",
        db_comment="Spotifyアーティスト名",
        max_length=255,
    )
    # --------------------------------------------------
    # その他トラックメタ情報
    # --------------------------------------------------
    # Spotify人気度
    spotify_popularity = models.PositiveSmallIntegerField(
        db_column="popularity",
        verbose_name="Spotify人気度",
        db_comment="Spotify人気度",
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100),
        ],
    )
    # Spotify再生時間(ms)
    spotify_duration_ms = models.PositiveIntegerField(
        db_column="spotify_duration_ms",
        verbose_name="Spotify再生時間(ms)",
        db_comment="Spotify再生時間(ms)",
        null=True,
        blank=True,
    )
    # Spotifyアルバム種別
    spotify_album_type = models.CharField(
        db_column="spotify_album_type",
        verbose_name="Spotifyアルバム種別",
        db_comment="Spotifyアルバム種別",
        choices=AlbumType.choices,
        null=True,
        blank=True,
    )
    # SpotifyアルバムID
    spotify_album_id = models.CharField(
        db_column="spotify_album_id",
        verbose_name="SpotifyアルバムID",
        db_comment="SpotifyアルバムID",
        max_length=255,
        null=True,
        blank=True,
    )
    # Spotifyアルバム名
    spotify_album_name = models.CharField(
        db_column="spotify_album_name",
        verbose_name="Spotifyアルバム名",
        db_comment="Spotifyアルバム名",
        max_length=255,
        null=True,
        blank=True,
    )
    # Spotifyリリース日(Spotifyは「2023」「2023-01」「2023-01-01」など形式が混在するためChar推奨)
    spotify_release_date = models.CharField(
        db_column="spotify_release_date",
        verbose_name="Spotifyリリース日",
        db_comment="Spotifyリリース日",
        max_length=20,
        null=True,
        blank=True,
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
            # 同一プレイリスト内で同一SpotifyID(曲ID)が重複しないようにする(論理削除考慮)
            UniqueConstraint(
                fields=["playlist", "spotify_id"],
                condition=Q(deleted_at__isnull=True),
                name="unique_t_playlist_track_playlist_spotify_id_active",
            ),
        ]

    def __str__(self):
        return f"{self.spotify_id} {self.spotify_name}"
