from django.conf import settings
from django.db import models


class BaseModel(models.Model):
    # ---------- Fields ----------
    # 作成者(削除/物理削除の場合は履歴を残すためSET_NULL)
    # created_by = models.CharField(db_column='created_by', verbose_name='作成者', db_comment='作成者', max_length=32, null=True, blank=True)
    created_by = models.ForeignKey(
        "account.M_User",
        db_column="created_by_id",
        verbose_name="作成者",
        db_comment="作成者",
        # 逆参照名を定義(例: 「参照先インスタンス.[related_name]」/通常参照は「本インスタンス.参照先モデル名(_id)」で取得可能)
        related_name="%(app_label)s_%(class)s_created_by",  # 関連名の一意性を確保
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    # 作成日時
    # auto_now_add はインスタンスの作成(DBにINSERT)する度に更新
    # created_at = models.DateTimeField(db_column='created_at', verbose_name='作成日時', db_comment='作成日時', auto_now_add=True, null=True, blank=True)
    created_at = models.DateTimeField(
        db_column="created_at",
        verbose_name="作成日時",
        db_comment="作成日時",
        null=True,
        blank=True,
        auto_now_add=True,
    )
    # 更新機能
    created_method = models.CharField(
        db_column="created_method",
        verbose_name="作成処理",
        db_comment="作成処理",
        max_length=128,
        null=True,
        blank=True,
    )
    # 更新者(削除/物理削除の場合は履歴を残すためSET_NULL)
    # updated_by = models.CharField(db_column='updated_by', verbose_name='更新者', db_comment='更新者', max_length=32, null=True, blank=True)
    updated_by = models.ForeignKey(
        "account.M_User",
        db_column="updated_by_id",
        verbose_name="更新者",
        db_comment="更新者",
        # 逆参照名を定義(例: 「参照先インスタンス.[related_name]」/通常参照は「本インスタンス.参照先モデル名(_id)」で取得可能)
        related_name="%(app_label)s_%(class)s_updated_by",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    # 更新日時
    # auto_now=Trueの場合はモデルインスタンスを保存する度に現在の時間で更新
    # updated_at = models.DateTimeField(db_column='updated_at', verbose_name='更新日時', db_comment='更新日時', auto_now=True, null=True, blank=True)
    updated_at = models.DateTimeField(
        db_column="updated_at",
        verbose_name="更新日時",
        db_comment="更新日時",
        null=True,
        blank=True,
        auto_now=True,
    )
    # 更新機能
    updated_method = models.CharField(
        db_column="updated_method",
        verbose_name="更新処理",
        db_comment="更新処理",
        max_length=128,
        null=True,
        blank=True,
    )
    # 削除日時
    deleted_at = models.DateTimeField(
        db_column="deleted_at",
        verbose_name="削除日時",
        db_comment="削除日時",
        null=True,
        blank=True,
        db_default=None,
        default=None,
    )

    class Meta:
        abstract = True
