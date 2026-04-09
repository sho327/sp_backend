import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q, UniqueConstraint
from simple_history.models import HistoricalRecords
# --- コアモジュール ---
from core.models import BaseModel

# ユーザ発行トークントラン
class T_UserToken(BaseModel):
    # ---------- Consts ----------
    class TokenTypes(models.TextChoices):
        ACTIVATION = "AC", "アカウント有効化"
        PASSWORD_RESET = "PR", "パスワードリセット"
        EMAIL_CHANGE = "EC", "メールアドレス変更確認"
    # ---------- Fields ----------
    # ID (BIGINT PRIMARY KEY) はDjangoが自動で付与
    # ユーザマスタ(削除/物理削除の場合はCASCADE)
    user = models.ForeignKey(
        "account.M_User",  # 循環参照対策(文字で定義することで、後での紐付けとする)
        db_column="user_id",
        verbose_name="ユーザマスタ",
        db_comment="ユーザマスタ",
        on_delete=models.CASCADE,
        # 逆参照名を定義(例: 「参照先インスタンス.[related_name]」/通常参照は「本インスタンス.参照先モデル名(_id)」で取得可能)
        related_name="user_t_user_token_set",
    )
    # トークン種別
    token_type = models.CharField(
        db_column="token_type",
        verbose_name="トークン種別",
        db_comment="トークン種別",
        max_length=2,
        choices=TokenTypes.choices,
    )
    # トークンハッシュ（SHA256など）
    token_hash = models.CharField(
        db_column="token_hash",
        verbose_name="トークンハッシュ（SHA256など）",
        db_comment="トークンハッシュ（SHA256など）",
        max_length=64,
    )
    # トークン有効期限
    expired_at = models.DateTimeField(
        db_column="expired_at",
        verbose_name="トークン有効期限",
        db_comment="トークン有効期限",
    )

    # 履歴管理不要: django-simple-historyを使用しない
    # history = HistoricalRecords()

    # テーブル名
    class Meta:
        db_table = "t_user_token"
        db_table_comment = "ユーザ発行トークントラン"
        verbose_name = "ユーザ発行トークントラン"
        verbose_name_plural = "ユーザ発行トークントラン"
        constraints = [
            # 未削除のトークン間でのみ token_hash をユニークにする
            UniqueConstraint(
                fields=["token_hash"],
                condition=Q(deleted_at__isnull=True),
                name="unique_t_user_token_token_hash_active",
            ),
        ]

    def __str__(self):
        return f"{self.user} - {self.token_hash[:10]}..."


# ログイン履歴
class T_LoginHistory(BaseModel):
    # ---------- Consts ----------
    class FailureReasons(models.TextChoices):
        PASSWORD_MISMATCH = "PASSWORD_MISMATCH", "パスワード不一致"
        LOCKED = "LOCKED", "アカウントロック中"
        NOT_ACTIVATED = "NOT_ACTIVATED", "アカウント未有効化"
        # MFA_FAILED = "MFA_FAILED", "2段階認証失敗"

    # ---------- Fields ----------
    # ID (BIGINT PRIMARY KEY) はDjangoが自動で付与
    # ユーザマスタ(削除/物理削除の場合はSET_NULL)
    user = models.ForeignKey(
        "account.M_User",  # 循環参照対策(文字で定義することで、後での紐付けとする)
        db_column="user_id",
        verbose_name="ユーザマスタ",
        db_comment="ユーザマスタ",
        on_delete=models.SET_NULL,
        # 逆参照名を定義(例: 「参照先インスタンス.[related_name]」/通常参照は「本インスタンス.参照先モデル名(_id)」で取得可能)
        related_name="user_t_login_history_set",
        null=True,
        blank=True,
    )
    # ログイン実行時の入力値（メールアドレス/ユーザーID）
    login_identifier = models.CharField(
        db_column="login_identifier",
        max_length=255,
        verbose_name="ログイン試行識別子",
        db_comment="ログイン試行識別子",
    )
    # 成功フラグ
    is_successful = models.BooleanField(
        db_column="is_successful",
        verbose_name="成功フラグ",
        db_comment="成功フラグ",
        db_index=True,
    )
    # ログイン失敗理由コード
    failure_reason = models.CharField(
        db_column="failure_reason",
        max_length=50,
        null=True,
        blank=True,
        verbose_name="ログイン失敗理由コード",
        db_comment="ログイン失敗理由コード",
        choices=FailureReasons.choices,
    )
    # IPアドレス
    ip_address = models.CharField(
        db_column="ip_address",
        max_length=45,
        null=True,
        blank=True,
        verbose_name="IPアドレス",
        db_comment="IPアドレス",
        help_text="クライアントのIPアドレス",
    )
    # クライアント情報
    user_agent = models.TextField(
        db_column="user_agent",
        null=True,
        blank=True,
        verbose_name="ユーザーエージェント",
        help_text="クライアントのブラウザ/OS情報",
        db_comment="ユーザーエージェント",
    )

    # 履歴管理不要: django-simple-historyを使用しない
    # history = HistoricalRecords()

    # テーブル名
    class Meta:
        db_table = "t_login_history"
        db_table_comment = "ログイン履歴トラン"
        verbose_name = "ログイン履歴トラン"
        verbose_name_plural = "ログイン履歴トラン"
        # ログイン試行が多い為、created_atとis_successfulで複合インデックスを貼る
        # indexes = [models.Index(fields=['created_at', 'is_successful'])]

    def __str__(self):
        # 参照先が存在しない場合を考慮
        identifier = self.user.email if self.user else self.login_identifier
        return f"{identifier} - {self.created_at}"


# プロフィールトラン
class T_Profile(BaseModel):
    # ---------- Consts ----------
    # アカウントステータスコード(アカウントの論理的なライフサイクル(最終的な利用可否))
    # 一時的な認証プロセスではなく、ユーザーの永続的な状態(退会、凍結、ロック)を示す
    class AccountStatues(models.IntegerChoices):
        ACTIVE = 10, "アクティブ"
        TEMPORARY_LOCKED = 30, "一時ロック"
        FROZEN = 40, "永続凍結"
        WITHDRAWN = 99, "退会済み"
    # ---------- Fields ----------
    # ユーザマスタ(削除/物理削除の場合はCASCADE)
    user = models.OneToOneField(
        "account.M_User",  # 循環参照対策(文字で定義することで、後での紐付けとする)
        db_column="user_id",
        verbose_name="ユーザマスタ",
        db_comment="ユーザマスタ",
        on_delete=models.CASCADE,
        primary_key=True,
        # 逆参照名を定義(例: m_user_instance.profile/通常参照はt_profile_instance.user_id(_id)で取得可能)
        related_name="user_t_profile_set",
    )
    # ユーザID(表のユーザID/固有の画面上での検索用のID)
    user_id_display = models.CharField(
        db_column="user_id_display",  # user_id(FK)と重複を避けるためdb_columnを調整
        verbose_name="ユーザID",
        db_comment="ユーザID",
        max_length=255,
    )
    # 表示名
    display_name = models.CharField(
        db_column="display_name",
        verbose_name="表示名",
        db_comment="表示名",
        max_length=255,
        null=True,
        blank=True,
    )
    # 所属
    affiliation = models.TextField(
        db_column="affiliation",
        verbose_name="所属",
        db_comment="所属",
        null=True,
        blank=True,
    )
    # 自己紹介
    bio = models.TextField(
        db_column="bio",
        verbose_name="自己紹介",
        db_comment="自己紹介",
        null=True,
        blank=True,
    )
    # アイコン(削除/物理削除の場合はCASCADE)
    icon = models.ForeignKey(
        "common.T_FileResource",
        db_column="icon_id",
        verbose_name="アイコン",
        db_comment="アイコン",
        on_delete=models.CASCADE,
        related_name="icon_t_profile_set",
        null=True,
        blank=True,
    )
    # 初期設定完了フラグ
    is_setup_completed = models.BooleanField(
        db_column="is_setup_completed",
        verbose_name="初期設定完了フラグ",
        db_comment="初期設定完了フラグ",
        db_default=False,
        default=False,
    )
    # ステータスコード(認証に必須なためM_Userモデルと1:1となるT_Profileに配置)
    status_code = models.IntegerField(
        db_column="status_code",
        verbose_name="ステータスコード",
        db_comment="ステータスコード",
        choices=AccountStatues.choices,
        db_default=AccountStatues.ACTIVE,
        default=AccountStatues.ACTIVE,
        db_index=True,
    )
    # ロック解除日時
    locked_until_at = models.DateTimeField(
        db_column="locked_until_at",
        verbose_name="ロック解除日時",
        db_comment="ロック解除日時",
        null=True,
        blank=True,
    )

    # django-simple-historyを使用
    history = HistoricalRecords()

    # テーブル名
    class Meta:
        db_table = "t_profile"
        db_table_comment = "プロフィールトラン"
        verbose_name = "プロフィールトラン"
        verbose_name_plural = "プロフィールトラン"
        constraints = [
            # アクティブな (is_active=True) かつ 未削除の (deleted_at__isnull=True) ユーザー間でのみ user_id がユニーク
            UniqueConstraint(
                fields=["user_id"],
                condition=Q(deleted_at__isnull=True),
                name="unique_t_profile_user_id_active",
            ),
        ]

    def __str__(self):
        return f"{self.display_name or self.user_id_display}"
