from datetime import datetime
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
# --- コアモジュール ---
from core.decorators.logging_process_with_sql import logging_process_with_sql
from core.consts import LOG_METHOD
from core.utils.log_helpers import log_output_by_msg_id
from core.utils.date_format import convert_to_site_timezone, date_to_str
from core.exceptions.exceptions import ApplicationError
# --- アカウントモジュール ---
from apps.account.serializer.password_reset_confirm import PasswordResetConfirmSerializer
from apps.account.services import AccountService

KINO_ID = "password-reset-confirm"

class PasswordResetConfirmView(APIView):
    """
    パスワードリセット実行APIクラス
    """
    permission_classes = [AllowAny]
    account_service = AccountService()

    @logging_process_with_sql(KINO_ID)
    def post(self, request, *args, **kwargs):
        try:
            return self.password_reset_confirm(request, *args, **kwargs)
        except ApplicationError:
            # ApplicationError関連はカスタムエラー処理が設定されている為そのまま親へスローする
            raise
        except Exception as e:
            # その他想定外エラーの場合もAPIエラーとする
            raise ApplicationError() from e

    def password_reset_confirm(self, request, *args, **kwargs):
        """
        パスワードリセット実行処理
        Args:
            request:  HTTPリクエスト
            *args:    引数
            **kwargs: キーワード引数
        Create
            Author: Kato Shogo
        """
        date_now: datetime = convert_to_site_timezone(timezone.now())
        # 1. 処理開始ログ出力(アプリケーションログ)
        log_output_by_msg_id(log_id="MSGI003", params=[KINO_ID, str(request.data)], logger_name=LOG_METHOD.APPLICATION.value)
        # 2. リクエストデータ検証
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # 3. パスワードリセット(サービス実行)
        self.account_service.password_reset_confirm(
            date_now=date_now,
            kino_id=KINO_ID, 
            **serializer.validated_data,
        )
        response_param = {
            "executeAt": date_to_str(target_date=date_now, target_format="%Y/%m/%d %H:%M:%S"),
        }
        # 4. 処理終了ログ出力(アプリケーションログ)
        log_output_by_msg_id(log_id="MSGI004", params=[KINO_ID, str(response_param)], logger_name=LOG_METHOD.APPLICATION.value)
        # 5. レスポンス返却
        return Response(response_param, status=status.HTTP_200_OK)
