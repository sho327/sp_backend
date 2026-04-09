import uuid
from django.utils import timezone
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.db.models import Q, UniqueConstraint
from simple_history.models import HistoricalRecords

from core.models import BaseModel

# SpotifyUserトークントラン
class T_SpotifyUserToken(BaseModel):
    # ---------- Consts ----------
    # ---------- Fields ----------
    # ID
    id = models.UUIDField(
        db_column="id",
        verbose_name="ID",
        db_comment="ID",
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    # メールアドレス
    email = models.EmailField(
        db_column="email",
        verbose_name="メールアドレス",
        db_comment="メールアドレス",
        max_length=254,  # RFC推奨の長さ設定
    )
    # アクセストークン
    access_token = models.TextField(
        db_column="access_token",
        verbose_name="アクセストークン",
        db_comment="アクセストークン",
    )
    # リフレッシュトークン
    refresh_token = models.TextField(
        db_column="refresh_token",
        verbose_name="リフレッシュトークン",
        db_comment="リフレッシュトークン",
    )
    # トークン有効期限
    expired_at = models.DateTimeField(
        db_column="expired_at",
        verbose_name="トークン有効期限",
        db_comment="トークン有効期限",
    )
    # リフレッシュロックフラグ
    refreshing = models.BooleanField(
        db_column="refreshing",
        verbose_name="リフレッシュロックフラグ",
        db_comment="リフレッシュロックフラグ",
        default=False,
    )
    # リフレッシュ更新ロック期限
    refreshing_until = models.DateTimeField(
        db_column="refreshing_until",
        verbose_name="リフレッシュ更新ロック期限",
        db_comment="リフレッシュ更新ロック期限",
        null=True,
        blank=True,
    )

    def is_expired(self):
        return timezone.now() >= self.expires_at

    def should_refresh(self):
        # 5分前に更新
        return timezone.now() >= self.expires_at - timedelta(minutes=5)

    def is_refreshing(self):
        if not self.refreshing:
            return False

        if self.refreshing_until and timezone.now() > self.refreshing_until:
            return False

        return True

    # django-simple-historyを使用
    # history = HistoricalRecords()

    # テーブル名
    class Meta:
        db_table = "t_spotify_user_token"
        db_table_comment = "SpotifyUserトークントラン"
        verbose_name = "SpotifyUserトークントラン"
        verbose_name_plural = "SpotifyUserトークントラン"
        constraints = [
            # 未削除のトークン間でのみemailをユニークにする
            # (M_User/T_Profileが必ず作られたユーザで認証するわけではないのでキーとしてはemailで管理※基本システムユーザのみ)
            UniqueConstraint(
                fields=["email"],
                condition=Q(deleted_at__isnull=True),
                name="unique_t_spotify_user_token_access_token_refresh_token_active",
            ),
        ]

    def __str__(self):
        return f"{self.access_token[:10]}..."


class T_AbstractAttachment(BaseModel):
    # ファイルリソース(削除/物理削除の場合はCASCADE)
    file_resource = models.ForeignKey(
        "common.T_FileResource",
        db_column="file_resource_id",
        verbose_name="ファイルリソース",
        db_comment="ファイルリソース",
        on_delete=models.CASCADE,
        related_name="file_resource_t_abstract_attachement_set",
        null=True,
        blank=True,
    )
    # 並び順
    order = models.IntegerField(
        db_column="order",
        verbose_name="並び順",
        db_comment="並び順",
        default=0
    )
  
    class Meta:
        abstract = True

# 例) 複数添付ファイルは下記のように抽象クラスを継承し定義する
# class T_PostAttachment(T_AbstractAttachment):
    # ファイルリソース(削除/物理削除の場合はCASCADE)
    # file_resource = models.ForeignKey(
    #     "post.T_Post",
    #     db_column="file_resource_id",
    #     verbose_name="ファイルリソース",
    #     db_comment="ファイルリソース",
    #     on_delete=models.CASCADE,
    #     related_name="file_resource_t_post_attachement_set",
    #     null=True,
    #     blank=True,
    # )

# ファイルリソーストラン
class T_FileResource(BaseModel):
    # ---------- Consts ----------
    # ファイル種別
    class FileType(models.TextChoices):
        IMAGE = "image", "画像"
        VIDEO = "video", "動画"
        PDF = "pdf", "PDF"
        OTHER = "other", "その他"

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
    # ファイル種別
    file_type = models.CharField(
        db_column="file_type",
        verbose_name="ファイル種別",
        db_comment="ファイル種別",
        max_length=20,
        choices=FileType.choices,
        default=FileType.OTHER,
    )
    # ファイルデータ
    file_data = models.FileField(
        db_column="file_data",
        verbose_name="ファイルデータ",
        db_comment="ファイルデータ",
        upload_to="file_resource/%Y/%m/%d/",  # 開発時は MEDIA_ROOT/file_resource/ に保存される
        null=True,
        blank=True,
    )
    # 外部URL(Spotifyの画像)
    external_url = models.URLField(
        db_column="external_url",
        verbose_name="外部URL",
        db_comment="外部URL",
        max_length=512,
        null=True,
        blank=True,
    )
    # ファイル名
    file_name = models.CharField(
        db_column="file_name",
        verbose_name="ファイル名",
        db_comment="ファイル名",
        max_length=255,
    )
    # ファイルサイズ
    file_size = models.BigIntegerField(
        db_column="file_size",
        verbose_name="ファイルサイズ",
        db_comment="ファイルサイズ",
        null=True,
        blank=True,
        help_text="単位: Byte"
    )

    @property
    def url(self):
        """
        内部ファイル/外部URL意識せずにURLを取得するためのプロパティ
        """
        if self.external_url:
            return self.external_url
        if self.file_data:
            return self.file_data.url
        return None

    # django-simple-historyを使用
    # history = HistoricalRecords()

    # テーブル名
    class Meta:
        db_table = "t_file_resource"
        db_table_comment = "ファイルリソーストラン"
        verbose_name = "ファイルリソーストラン"
        verbose_name_plural = "ファイルリソーストラン"
        constraints = [
            # 未削除のレコード内でのみ、外部リソースがが重複しないことを保証
            UniqueConstraint(
                fields=["external_url"],
                # external_url が null でない場合のみチェック
                condition=Q(deleted_at__isnull=True) & Q(external_url__isnull=False),
                name="unique_t_file_resource_external_url_active",
            ),
        ]

    def __str__(self):
        return f"{self.file_name}"
