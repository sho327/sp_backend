import os
from typing import List, Optional
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse

# --- コアモジュール ---
from core.consts import LOG_METHOD
from core.utils.log_helpers import log_output_by_msg_id
from core.exceptions.exceptions import ExternalServiceError

# --- アカウントモジュール ---
from apps.account.models import M_User

User: M_User = get_user_model()


class EmailService:
    """
    アプリケーションで発生するメール送信処理を一括管理するサービス。
    外部通信の責務をビジネスロジックから分離する。
    """

    def __init__(self):
        pass

    def _get_site_url(self, path: str) -> str:
        """Siteフレームワークと設定に基づき絶対URLを構築するヘルパー"""
        current_site = Site.objects.get_current()
        domain = current_site.domain
        # settings.DEBUGに応じてスキームを切り替え(元のロジックを維持)
        scheme = "https" if not settings.DEBUG else "http"
        return f"{scheme}://{domain}{path}"

    def _send_email(
        self,
        subject: str,
        message: str,
        recipient_list: List[str],
        html_message: Optional[str] = None,
    ) -> bool:
        """
        全てのメール送信が通る共通エントリーポイント。
        全てのメール処理の変更は、このメソッド内部で行う。
        Args:
            subject: メールの件名
            message: プレーンテキストのメール本文
            recipient_list: 受信者のメールアドレスリスト
            html_message: HTMLメール本文（指定された場合、これが優先される）
        Returns:
            送信成功時True
        Raises:
            ExternalServiceError: メール送信に失敗した場合
        """
        if not recipient_list:
            return False

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.EMAIL_FROM,
                recipient_list=recipient_list,
                # html_message が None なら None のまま渡す
                html_message=html_message,
                fail_silently=False,
            )
            return True
        except Exception as e:
            # メールの送信に失敗した場合、ログ出力後呼び出し元へエラーを返す
            log_output_by_msg_id(log_id="MSGE003", params=[settings.EMAIL_FROM, recipient_list, subject, message, html_message], logger_name=LOG_METHOD.APPLICATION.value)
            # 外部サービスのエラーとして例外を投げる
            raise ExternalServiceError()

    def send_templated_email(
        self,
        subject: str,
        recipient_list: List[str],
        template_name: str,
        context: dict,
    ) -> bool:
        """
        テンプレートを使ってメールを作成し、送信する。

        Args:
            subject: メールの件名
            recipient_list: 受信者のメールアドレスリスト
            template_name: 使用するテンプレート名（例: 'emails/activation_email.html'）
            context: テンプレートに渡すコンテキスト辞書

        Returns:
            送信成功時True

        Raises:
            ExternalServiceError: メール送信に失敗した場合
        """
        if not recipient_list:
            return False

        try:
            # テンプレートをレンダリングしてHTML本文を生成
            html_message = render_to_string(template_name, context)
        except Exception as e:
            # メールの送信に失敗した場合、ログ出力後呼び出し元へエラーを返す
            log_output_by_msg_id(log_id="MSGE003", params=[settings.EMAIL_FROM, recipient_list, subject, template_name, str(context)], logger_name=LOG_METHOD.APPLICATION.value)
            # テンプレートレンダリングエラーも含めてExternalServiceErrorとして扱う
            raise ExternalServiceError()

        # 共通メソッドで送信(HTMLメールとして送信)
        return self._send_email(
            subject=subject,
            message="",  # HTMLメールなのでプレーンテキストは空
            recipient_list=recipient_list,
            html_message=html_message,
        )
        

    def send_activation_email(self, user: M_User, raw_token_value: str):
        """
        アクティベーションメールを送信する。
        """
        # 1. URLの構築
        # Djangoのreverseを使わず、フロントエンドのURLを構築
        frontend_base_url = f"{settings.FRONTEND_URL}/account/activate"
        activation_url = f"{frontend_base_url}?token={raw_token_value}"

        # 2. メール本文の生成(元のロジックを維持)
        expiry_seconds = settings.TOKEN_EXPIRY_SECONDS["account_activation"]
        expiry_hours = expiry_seconds / 3600

        subject = f"【{settings.APP_NAME}】仮登録完了のお知らせ"
        message = (
            f"{settings.APP_NAME}にご登録いただきありがとうございます。\n"
            f"次のリンクをクリックしてアカウントを有効化してください（有効期限：{expiry_hours}時間）。\n"
            f"{activation_url}"
        )

        # 3. 共通メソッドで送信
        self._send_email(subject, message, [user.email])

    def send_password_reset_email(self, user: M_User, display_name: str, raw_token: str):
        """
        パスワードリセットメールを送信する。
        AuthServiceからdisplay_nameとraw_tokenを受け取る。
        """
        # 1. URLの構築
        # 元コードはハードコードされていたため、一時的に再現
        reset_url = self._get_site_url(f"/account/password_reset_confirm/{raw_token}/")

        # 2. メール本文の生成(元のロジックを維持)
        expiry_seconds = settings.TOKEN_EXPIRY_SECONDS["password_reset"]
        expiry_hours = expiry_seconds / 3600

        subject = f"【{settings.APP_NAME}】パスワード再設定のご案内"
        message = (
            f"{display_name} 様\n\n"
            f"パスワード再設定のリクエストを受け付けました。\n"
            f"以下のリンクから新しいパスワードを設定してください（有効期限：{expiry_hours}時間）。\n\n"
            f"{reset_url}\n\n"
            f"お心当たりがない場合は、このメールを破棄してください。"
        )

        # 3. 共通メソッドで送信
        self._send_email(subject, message, [user.email])
