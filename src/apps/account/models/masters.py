import uuid

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.db.models import Q, UniqueConstraint
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords
# --- コアモジュール ---
from core.models import BaseModel


class M_UserManager(BaseUserManager):
    def get_by_natural_key(self, username):
        # 組み込みメソッド: 「USERNAME_FIELD」で指定されたフィールドの内容を使用してユーザーインスタンスを取得
        # ログイン時に「削除されていないユーザー」のみを対象にする
        # 以下はuser_nameフィールドにユニークが掛かっていることが前提の動きになるので、オーバーライドし回避
        return self.get(**{f"{self.model.USERNAME_FIELD}": username, "deleted_at__isnull": True})
    
    def create_user(self, email, password=None, kino_id="m_user-manager", **extra_fields):
        if not email:
            raise ValueError("Emailは必須です")
        # デフォルト値の設定
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_active", False)  # 初期は非アクティブ(メール認証等を想定)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("created_method", kino_id)
        extra_fields.setdefault("updated_method", kino_id)
        user: M_User = self.model(
            email=self.normalize_email(email),
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


# ユーザーマスタ
class M_User(AbstractBaseUser, BaseModel, PermissionsMixin):
    """
    認証専用のモデル。
    将来的に SupabaseAuth(auth.users)等の他の認証に置き換えれるよう最低限の実装。
    """
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
        unique=False,  # 論理削除を考慮し、unique=Trueは外してConstraintsで制御
    )
    # パスワード (AbstractBaseUserで定義されているが、列順序制御のため明示)
    password = models.CharField(
        db_column="password",
        verbose_name="パスワード",
        db_comment="パスワード",
        max_length=128,
    )
    # 最終ログイン
    last_login = models.DateTimeField(
        db_column="last_login",
        verbose_name="最終ログイン",
        db_comment="最終ログイン",
        null=True,
        blank=True,
    )
    # 有効フラグ(管理サイトに入れるか、その他Djangoパッケージで有効なユーザかの判定で使用される)
    is_active = models.BooleanField(
        db_column="is_active",
        verbose_name="有効フラグ",
        db_comment="有効フラグ",
        db_default=False,
        default=False,
    )
    # 一般ユーザフラグ(管理サイトに一般ユーザとして入れるか)
    is_staff = models.BooleanField(
        db_column="is_staff",
        verbose_name="一般ユーザフラグ",
        db_comment="一般ユーザフラグ",
        db_default=False,
        default=False,
    )
    # 管理者フラグ(管理サイトに管理者として入れるか)
    is_superuser = models.BooleanField(
        db_column="is_superuser",
        verbose_name="管理者フラグ",
        db_comment="管理者フラグ",
        db_default=False,
        default=False,
    )
    # PermissionsMixinのフィールド
    groups = models.ManyToManyField(
        to="auth.Group",
        verbose_name=_("groups"),
        blank=True,
        related_name="group_m_user_set",
        # related_query_name="group_m_user_set",
    )
    user_permissions = models.ManyToManyField(
        to="auth.Permission",
        verbose_name=_("user permissions"),
        blank=True,
        related_name="user_permissions_m_user_set",
        # related_query_name="user_permissions_m_user_set",
    )

    ### カスタム定義 ###
    objects = M_UserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # emailはUSERNAME_FIELDなので不要

    # django-simple-historyを使用
    history = HistoricalRecords()

    # MetaSettings
    class Meta:
        db_table = "m_user"
        db_table_comment = "ユーザーマスタ"
        verbose_name = "ユーザーマスタ"
        verbose_name_plural = "ユーザーマスタ"
        constraints = [
            # 有効かつ未削除のユーザー間でのみ email がユニーク
            UniqueConstraint(
                fields=["email"],
                condition=Q(deleted_at__isnull=True), # is_active=Trueは入れない(メール認証待ちユーザ含めて1件のみしか作成不可とする)
                name="unique_m_user_email_active",
            ),
        ]

    def __str__(self):
        return f"{self.email}"
