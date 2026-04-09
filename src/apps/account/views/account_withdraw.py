from datetime import datetime
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
# --- コアモジュール ---
from core.decorators.logging_process_with_sql import logging_process_with_sql
from core.consts import LOG_METHOD
from core.utils.log_helpers import log_output_by_msg_id
from core.utils.date_format import convert_to_site_timezone, date_to_str
from core.exceptions.exceptions import ApplicationError
# --- アカウントモジュール ---
from apps.account.services import AccountService

KINO_ID = "account-withdraw"

class AccountWithdrawView(APIView):
    """
    退会処理APIクラス
    Create
        Author: Kato Shogo
    """
    permission_classes = [IsAuthenticated]
    account_service = AccountService()

    @logging_process_with_sql(KINO_ID)
    def post(self, request, *args, **kwargs):
        """
        POSTリクエストを受け付ける。
        Method: POST
        Args:
            request:  HTTPリクエスト
            *args:    引数
            **kwargs: キーワード引数
        Returns:
            Response: HTTPレスポンス
        Raises:
            InternalServerError: 想定外エラー
        Create
            Author: Kato Shogo
        """
        try:
            return self.account_withdraw(request, *args, **kwargs)
        except ApplicationError:
            # ApplicationError関連はカスタムエラー処理が設定されている為そのまま親へスローする
            raise
        except Exception as e:
            # その他想定外エラーの場合もAPIエラーとする
            raise ApplicationError() from e
    
    def account_withdraw(self, request, *args, **kwargs):
        """
        アカウント退会処理
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
        # 2. ログイン(サービス実行)
        self.account_service.account_withdraw(date_now, KINO_ID, request.user.id)
        # 3. レスポンス作成
        response_param = {
            "executeAt": date_to_str(target_date=date_now, target_format="%Y/%m/%d %H:%M:%S"),
        }
        # 4. 処理終了ログ出力(アプリケーションログ)
        log_output_by_msg_id(log_id="MSGI004", params=[KINO_ID, str(response_param)], logger_name=LOG_METHOD.APPLICATION.value)
        # 5. レスポンス返却
        return Response(response_param, status=status.HTTP_200_OK)
