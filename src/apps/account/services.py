import secrets, hashlib, uuid
from typing import Dict
from datetime import datetime
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import update_last_login
from django.db import transaction, IntegrityError
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

# --- コアモジュール ---
from core.consts import LOG_METHOD
from core.utils.log_helpers import log_output_by_msg_id

# --- 共通モジュール ---
from apps.common.services.email_service import EmailService

# --- アカウントモジュール ---
from apps.account.exceptions import (
    AccountLockedError,
    AuthenticationFailedError,
    PasswordResetTokenInvalidError,
    EmailDuplicationError,
    TokenExpiredOrNotFoundError,
    UserAlreadyActiveError,
    UserNotFoundError,
)
from apps.account.models import M_User, T_UserToken, T_LoginHistory, T_Profile


User: M_User = get_user_model()

class AccountService:
    """
    認証（ログイン、ログアウト）、認可、
    およびクレデンシャル管理（パスワードリセット等）を担うサービスクラス
    """

    def __init__(self):
        # サービス内で別のサービスを保持する
        self.email_service = EmailService()

    # ------------------------------------------------------------------
    # ユーザトークン作成処理
    # ------------------------------------------------------------------
    def _create_user_token(
        self, 
        user: M_User, 
        token_type: T_UserToken.TokenTypes, 
        date_now: datetime,
        kino_id: str, 
        expires_hours: int = 24,
    ) -> str:
        """
        指定されたタイプのハッシュ化トークンを生成・保存し、生のトークンを返す。
        """
        expires_at = date_now + timezone.timedelta(hours=expires_hours)
        max_retries = 3
        
        for attempt in range(max_retries):
            # 1. 生のセキュアトークンを生成
            raw_token = secrets.token_urlsafe(32)
            # 2. ハッシュ化(DB保存用)
            token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

            try:
                # データベース操作をアトミックに実行(IntegrityError後のループ時にも再試行分は確定させたいため)
                with transaction.atomic():
                    # 4. 同タイプの古いトークンを無効化(最初の試行時のみ実行)
                    if attempt == 0:
                        T_UserToken.objects.filter(
                            user=user,
                            token_type=token_type,
                            deleted_at__isnull=True,
                        ).update(
                            updated_by=user,
                            # updated_at=date_now,
                            updated_method=kino_id,
                            deleted_at=date_now,
                        )
                    # 5. トークンの作成
                    T_UserToken.objects.create(
                        user=user,
                        token_type=token_type,
                        token_hash=token_hash,
                        expired_at=expires_at,
                        created_by=user,
                        created_method=kino_id,
                        updated_by=user,
                        updated_method=kino_id,
                    )
                # 成功したらループを抜けてトークンを返す
                return raw_token
            except IntegrityError:
                # 最後の試行でもエラーが出た場合は、そのまま例外を投げる
                if attempt == max_retries - 1:
                    # 最大リトライまで失敗した場合、ログ出力後呼び出し元へエラーを返す
                    log_output_by_msg_id(log_id="MSGE001", params=[f"Token collision persists after {max_retries} retries."], logger_name=LOG_METHOD.APPLICATION.value)
                    raise
                continue
    
    # ------------------------------------------------------------------
    # ログイン試行回数カウント/ロック処理
    # ------------------------------------------------------------------
    def _count_or_lock_login_failure(self, date_now: datetime, kino_id: str, user: M_User | None, email :str, ip_address: str | None, user_agent: str | None):
        # 履歴を保存
        self._save_login_history(kino_id, user, email, False, T_LoginHistory.FailureReasons.PASSWORD_MISMATCH, ip_address, user_agent)
        
        # 直近15分以内の失敗回数をカウント(例: 5回でロック)
        recent_failures = T_LoginHistory.objects.filter(
            user=user, 
            is_successful=False, 
            created_at__gt=date_now - timezone.timedelta(minutes=15)
        ).count()

        if recent_failures >= 5:
            t_profile_instance: T_Profile = user.user_t_profile_set
            t_profile_instance.status_code = T_Profile.AccountStatues.TEMPORARY_LOCKED
            t_profile_instance.locked_until_at = date_now + timezone.timedelta(minutes=30) # 30分ロック
            t_profile_instance.updated_by = user
            t_profile_instance.updated_method = kino_id
            t_profile_instance.save()

    # ------------------------------------------------------------------
    # ログイン履歴の登録処理
    # ------------------------------------------------------------------
    def _save_login_history(self, kino_id: str, user: M_User | None, identifier: str, is_success: bool, reason: str, ip_address: str | None, user_agent: str | None):
        T_LoginHistory.objects.create(
            user=user,
            login_identifier=identifier,
            is_successful=is_success,
            failure_reason=reason,
            ip_address=ip_address,
            user_agent=user_agent,
            created_by=user,
            created_method=kino_id,
            updated_by=user,
            updated_method=kino_id,
        )

    # ------------------------------------------------------------------
    # 新規登録処理
    # ------------------------------------------------------------------
    def signup(self, date_now: datetime, kino_id: str, email: str, password: str) -> M_User:
        """
        メールアドレスとパスワードで新規登録する。
        Args:
            email (str): メールアドレス
            password (str): パスワード
        Returns:
            M_User: 作成されたユーザーインスタンス
        Raises:
            EmailDuplicationError: アカウントが既に存在する(メールアドレスが重複している)
            IntegrityError: その他重複エラー(リトライ回数を超えてもトークンハッシュが重複している等)
        """
        # 1. ユーザ存在チェック
        if User.objects.filter(email=email, is_active=True, deleted_at__isnull=True).exists():
            raise EmailDuplicationError()

        # 2. ユーザ作成
        try:
            m_user_instance: M_User = User.objects.create_user(
                email=email, 
                password=password,
                kino_id=kino_id,
            )
        except IntegrityError:
            # 重複が発生した場合の処理(一意制約に違反した場合/"email"が競合していた場合)
            # config.settings設定に沿って、ロールバックさせる
            raise EmailDuplicationError()
        
        # 3. トークン作成
        # 内部からエラーが投げられた場合、config.settings設定に沿って、ロールバックさせる
        raw_token: T_UserToken = self._create_user_token(
            user=m_user_instance, 
            token_type=T_UserToken.TokenTypes.ACTIVATION, 
            date_now=date_now,
            kino_id=kino_id,
        )

        # 4. メール送信(コミット成功後のみ実行)
        # トランザクション確定後に送ることで、メールは送ったがコミット失敗のようなリスクを回避する
        # ※メール送信に失敗した場合は、ログ出力されるので手動での再送信が必要
        # transaction.on_commit(lambda: self.email_service.send_activation_email(m_user_instance, raw_token))

        # トランザクション確定前に送り、送信に失敗した場合はロールバックさせる
        # コミットに失敗した場合、メールだけ送信されるがその場合は再度新規登録してもらえれば、
        # 管理者からはメール再送信等の手間なく運用可能
        self.email_service.send_activation_email(m_user_instance, raw_token)
    
    # ------------------------------------------------------------------
    # ユーザアクティベーション処理
    # ------------------------------------------------------------------
    def activate_user(self, date_now: datetime, kino_id: str, raw_token: str) -> M_User:
        """
        アクティベーションリンクに含まれる生トークンを使用してユーザーを有効化する。
        Args:
            raw_token (str): URLから取得した生トークン値
        Returns:
            User: 有効化されたユーザーインスタンス
        Raises:
            TokenExpiredOrNotFoundError: トークンが見つからないか、期限切れの場合
            UserAlreadyActiveError: ユーザーが既に有効な場合
        """
        # 1. 生トークンをDBに保存されている形式（ハッシュ値）に変換
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        # 2. 条件に合うトークンの検索(ハッシュ値、種別、未期限切れ、未削除を条件とする)
        t_user_token_instance: T_UserToken = T_UserToken.objects.filter(
            token_hash=token_hash,
            token_type=T_UserToken.TokenTypes.ACTIVATION,
            expired_at__gt=date_now,  # 現在時刻より期限が未来であること
            deleted_at__isnull=True,
        ).first()

        if not t_user_token_instance:
            # トークンが存在しない、または期限切れ
            raise TokenExpiredOrNotFoundError()

        m_user_instance: M_User = t_user_token_instance.user

        # 3. ユーザーの状態チェック
        # アカウント有効化の処理となるのでメール認証済みフラグは見ない => 詳細は「docs/ユーザの状態管理について.md」参照)
        if m_user_instance.is_active:
            # トークンが見つかったがユーザーは既にアクティブ
            # この場合も、セキュリティのため使用済みトークンとして無効化する
            t_user_token_instance.updated_by = m_user_instance
            # t_user_token_instance.updated_at = date_now
            t_user_token_instance.updated_method = kino_id
            t_user_token_instance.deleted_at = date_now
            t_user_token_instance.save()
            raise UserAlreadyActiveError()

        # 4. ユーザーをシステム的にログイン可能(アクティブ)にする
        m_user_instance.is_active = True
        m_user_instance.updated_by = m_user_instance
        # m_user_instance.updated_at = date_now
        m_user_instance.updated_method = kino_id
        m_user_instance.save()

        # 5. 使用済みのトークンを無効化(論理削除)
        t_user_token_instance.updated_by = m_user_instance
        # t_user_token_instance.updated_at = date_now
        t_user_token_instance.updated_method = kino_id
        t_user_token_instance.deleted_at = date_now
        t_user_token_instance.save()
    
    # ------------------------------------------------------------------
    # ログイン処理(JWT発行)
    # ------------------------------------------------------------------
    def login(self, date_now: datetime, kino_id: str, email: str, password: str, ip_address: str = None, user_agent: str = None) -> Dict[str, str]:
        """
        メールアドレスとパスワードでログインし、JWTトークンペアを返す。
        Args:
            email (str): メールアドレス
            password (str): パスワード
        Returns:
            Dict[str, str]: {"access": "...", "refresh": "..."}
        Raises:
            AuthenticationFailedError: 認証失敗
            AccountLockedError: アカウントが無効（is_active=False）
        """
        # 1. ユーザーの事前取得(ロック状態確認のため)
        m_user_instance1: M_User = User.objects.filter(email=email, deleted_at__isnull=True).first()
        if m_user_instance1:
            # プロフィール取得(OneToOne)
            t_profile_instance: T_Profile = getattr(m_user_instance1, 'user_t_profile_set', None)
            
            # A. ステータスによる永続的な拒否(退会済み・凍結)
            if t_profile_instance and t_profile_instance.status_code in [T_Profile.AccountStatues.FROZEN, T_Profile.AccountStatues.WITHDRAWN]:
                self._save_login_history(kino_id, m_user_instance1, email, False, T_LoginHistory.FailureReasons.LOCKED, ip_address, user_agent)
                raise AccountLockedError()
            
            # B. 一時ロックの期限チェック
            if t_profile_instance and t_profile_instance.status_code == T_Profile.AccountStatues.TEMPORARY_LOCKED:
                if t_profile_instance.locked_until_at and t_profile_instance.locked_until_at > date_now:
                    self._save_login_history(kino_id, m_user_instance1, email, False, T_LoginHistory.FailureReasons.LOCKED, ip_address, user_agent)
                    raise AccountLockedError()
            
            # C. ロック・対応済み・凍結の場合以外(メール認証待ちユーザからのログイン等)で未アクティブの場合もエラーとする
            if not m_user_instance1.is_active:
                self._save_login_history(kino_id, m_user_instance1, email, False, T_LoginHistory.FailureReasons.NOT_ACTIVATED, ip_address, user_agent)
                raise AuthenticationFailedError()

        # 2. 認証実行
        m_user_instance2: M_User = authenticate(email=email, password=password)
        if m_user_instance2 is None:
            try:
                # 認証失敗時の処理(失敗回数のカウントやロック判定)
                if m_user_instance1:
                    self._count_or_lock_login_failure(date_now, kino_id, m_user_instance1, email, ip_address, user_agent)
                else:
                    # 存在しないユーザーの場合も履歴だけ残す
                    self._save_login_history(kino_id, None, email, False, T_LoginHistory.FailureReasons.PASSWORD_MISMATCH, ip_address, user_agent)
            except Exception as e:
                # 履歴保存自体のエラーでログインエラーが上書きされないようにログのみ
                log_output_by_msg_id(log_id="MSGE001", params=[f"Failed to save login history: {str(e)}"], logger_name=LOG_METHOD.APPLICATION.value)
            # ユーザーが存在しないか、パスワードが不一致エラー
            raise AuthenticationFailedError()

        # 3. 認証成功時の処理
        # パスワードが合致した後の「状態更新」は一塊の処理として原子性を保証する
        try:
            with transaction.atomic():
                # A. 最終ログイン日時の更新
                update_last_login(None, m_user_instance2)
                
                # B. ロック解除(必要な場合のみ)
                if t_profile_instance and t_profile_instance.status_code == T_Profile.AccountStatues.TEMPORARY_LOCKED:
                    t_profile_instance.status_code = T_Profile.AccountStatues.ACTIVE
                    t_profile_instance.locked_until_at = None
                    t_profile_instance.updated_by = m_user_instance2
                    t_profile_instance.updated_method = kino_id
                    t_profile_instance.save()
                
                # C. 成功履歴の保存
                self._save_login_history(kino_id, m_user_instance2, email, True, None, ip_address, user_agent)
        except Exception as e:
            # ここでエラーが起きた場合は、中途半端な更新をロールバックし、ログイン自体を失敗させる(トークンを返さない)
            log_output_by_msg_id(log_id="MSGE001", params=[f"Success process failed: {str(e)}"], logger_name=LOG_METHOD.APPLICATION.value)
            raise AuthenticationFailedError()

        # 4. JWTトークンの生成(SimpleJWT利用)
        refresh = RefreshToken.for_user(m_user_instance2)
        return {
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
        }

    # ------------------------------------------------------------------
    # パスワードリセット(メール送信)
    # ------------------------------------------------------------------
    def password_reset(self, date_now: datetime, kino_id: str, email: str) -> bool:
        """
        パスワードリセットメールを送信する。
        セキュリティ上の理由から、ユーザーが存在しなくてもエラーにはせずTrueを返す(列挙攻撃対策)。
        """
        # 1. ユーザー検索
        m_user_instance: M_User = User.objects.filter(email=email, deleted_at__isnull=True).first()
        # ユーザーが存在しない、またはアクティブでない場合は何もしないが、攻撃者に悟られないよう正常終了を装う
        if not m_user_instance or not m_user_instance.is_active:
            return True
        
        # 2. 短時間(例: 1分以内)の重複リクエストをチェック
        # ※再送信したはずが、メールが2通届いていない問い合わせが来る可能性
        # ※ただし、「既に送信済みです」といったエラーとし、列挙攻撃されるリスクが高くなる可能性も考慮し、
        # 以下で対応としたい
        # ---------------------------------------------
        # 案1：フロントエンド（画面側）で制御
        # APIは常にTrueを返すが、画面側で「再送ボタン」を1分間非活性(グレーアウト)にしたり、カウントダウンを表示したりする
        # => ユーザーに「今は送れない」ことが伝わる。APIのセキュリティも守れる。
        # ---------------------------------------------
        # 案2：APIメッセージを「曖昧」にする
        # 「入力されたアドレスが登録されている場合、再設定メールを送信しました。届かない場合は、1分以上空けてから再度お試しください」といった文言を常に表示。
        # => ユーザーに「1分待つ必要がある」という仕様を事前に伝えられる。
        one_minute_ago = date_now - timezone.timedelta(minutes=1)
        recent_token_exists = T_UserToken.objects.filter(
            user=m_user_instance,
            token_type=T_UserToken.TokenTypes.PASSWORD_RESET,
            created_at__gt=one_minute_ago,
            deleted_at__isnull=True
        ).exists()
        if recent_token_exists:
            # 1分以内で既に送信済みの場合は再送信させず、攻撃者に悟られないよう正常終了を装う
            # 既に送信されているメールを確認
            return True

        # 3. 共通メソッドでリセット用トークンを発行(有効期限は短めの1時間など)
        raw_token = self._create_user_token(
            user=m_user_instance,
            token_type=T_UserToken.TokenTypes.PASSWORD_RESET,
            date_now=date_now,
            kino_id=kino_id,
            expires_hours=1,
        )

        # 4. プロフィールの取得(OneToOneなので.first()または直接取得でOK)
        display_name = ""
        profile: T_Profile = getattr(m_user_instance, 'user_t_profile_set', None)
        # 表示名の取得
        if profile and profile.display_name:
            display_name = profile.display_name
        else:
            # ログを出して管理者には異常を知らせるが、処理は止めない
            log_output_by_msg_id(log_id="MSGE001", params=[f"T_Profile missing for user: {email}"], logger_name=LOG_METHOD.APPLICATION.value)
            display_name = email.split('@')[0]

        # 5. メール送信(コミット成功後のみ実行)
        # トランザクション確定後に送ることで、メールは送ったがコミット失敗のようなリスクを回避する
        # ※メール送信に失敗した場合は、ログ出力されるので手動での再送信が必要
        # transaction.on_commit(lambda: self.email_service.send_password_reset_email(m_user_instance, raw_token))

        # トランザクション確定前に送り、送信に失敗した場合はロールバックさせる
        # コミットに失敗した場合、メールだけ送信されるがその場合は再度パスワードリセットしてもらえれば、
        # 管理者からはメール再送信等の手間なく運用可能
        self.email_service.send_password_reset_email(m_user_instance, display_name, raw_token)

        return True

    # ------------------------------------------------------------------
    # パスワードリセット実行
    # ------------------------------------------------------------------
    def password_reset_confirm(self, date_now: datetime, kino_id: str, raw_token: str, new_password: str) -> M_User:
        """
        トークンを検証し、パスワードを更新する。
        """
        # 1. 生トークンをDBに保存されている形式（ハッシュ値）に変換
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        # 2. トークンを検索（ハッシュ値、種別、未期限切れ、未削除を条件とする）
        t_user_token_instance: T_UserToken = T_UserToken.objects.filter(
            token_hash=token_hash,
            token_type=T_UserToken.TokenTypes.PASSWORD_RESET,
            expired_at__gt=date_now,  # 現在時刻より期限が未来であること
            deleted_at__isnull=True,
        ).first()
        if not t_user_token_instance:
            # トークンが存在しない、または期限切れ
            raise PasswordResetTokenInvalidError()

        m_user_instance: M_User = t_user_token_instance.user

        # 2. パスワード更新 (ハッシュ化はset_passwordが担う)
        m_user_instance.set_password(new_password)
        m_user_instance.updated_by = m_user_instance
        m_user_instance.updated_method = kino_id
        m_user_instance.save()

        # 3. 使用済みトークンを無効化
        t_user_token_instance.expired_at = date_now
        t_user_token_instance.updated_by = m_user_instance
        t_user_token_instance.updated_method = kino_id
        t_user_token_instance.deleted_at = date_now
        t_user_token_instance.save()

        # ------------------------------------------------------------------
        # 5. 【セキュリティ強化：全デバイスからの強制ログアウト（セッション切断）】
        #    パスワード変更により、不正アクセス者による他のセッション利用を防ぐために行う。
        #    ※ 現在は実装しないが、将来的な拡張ポイントとしてコメントで残す。
        # ------------------------------------------------------------------
        # ▼ 実現方法 1: リフレッシュトークンの削除 (推奨/ソフトコミット)
        #    T_UserTokenにリフレッシュトークンを保存している場合、
        #    そのユーザーIDに紐づく全てのリフレッシュトークンを削除する。
        #    # self.token_repo.invalidate_tokens_by_user(user, TokenTypes.REFRESH)

        # ▼ 実現方法 2: JWTアクセストークンのブラックリスト化 (即時切断/負荷高)
        #    SimpleJWTのブラックリスト機能（通常Redisなどのキャッシュを使用）を利用し、
        #    ユーザーの全JWTを強制的に失効させる。

        # ▼ 実現方法 3: 伝統的なDjangoセッションの削除
        #    django.contrib.sessions の機能を利用し、ユーザーに紐づくDB上の全セッションを削除する。
        #    # from django.contrib.sessions.models import Session
        #    # Session.objects.filter(expire_date__gte=timezone.now(), session_key__in=Session.objects.filter(session_key=user.pk).values_list('session_key', flat=True)).delete()
        # ------------------------------------------------------------------

        return m_user_instance

    # ------------------------------------------------------------------
    # 退会処理(論理削除)
    # ------------------------------------------------------------------
    def account_withdraw(self, date_now: datetime, kino_id: str, user_id: uuid.UUID) -> None:
        """
        ユーザーのアカウントを無効化し、論理削除を行う。
        """
        # 1. ユーザーと関連プロフィールの取得(select_relatedを設定しておくことで、後のプロフィール更新時のクエリを減らす)
        user: M_User = User.objects.filter(id=user_id, deleted_at__isnull=True).select_related('user_t_profile_set').first()
        if not user:
            # 既に削除されているまたは存在しない場合
            raise UserNotFoundError()

        # 2. ユーザーの状態を退会済みに更新(is_active=Falseにすることでauthenticateやloginを通らなくする)
        user.is_active = False
        user.updated_by = user
        user.updated_method = kino_id
        user.deleted_at = date_now
        user.save()

        # 3. プロフィールも論理削除(OneToOneなので.first()または直接取得でOK)
        profile: T_Profile = getattr(user, 'user_t_profile_set', None)
        if profile:
            profile.updated_by = user
            profile.updated_method = kino_id
            profile.deleted_at = date_now
            profile.save()

        # 4. 保有している全ての有効なトークン(アクティベーション、パスワードリセット等)を無効化
        T_UserToken.objects.filter(
            user=user, 
            deleted_at__isnull=True,
        ).update(
            updated_by=user,
            updated_method=kino_id,
            deleted_at=date_now,
        )

        # 4. 必要であれば、ここでリフレッシュトークンのブラックリスト化などを行う
        # SimpleJWTを使用している場合、OutstandingToken等から削除するロジックをここに入れる
        return None