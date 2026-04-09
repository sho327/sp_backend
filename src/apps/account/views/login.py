from datetime import datetime
from django.utils import timezone
from django.db import transaction
from django.utils.decorators import method_decorator
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
from apps.account.serializer.login import LoginSerializer
from apps.account.services import AccountService

KINO_ID = "login"

class LoginView(APIView):
    """
    ログイン処理APIクラス
    Create
        Author: Kato Shogo
    """
    permission_classes = [AllowAny]
    account_service = AccountService()

    # このメソッド内でのDB操作(履歴保存等)は実行された瞬間にDBに確定(コミット)される
    @method_decorator(transaction.non_atomic_requests)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

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
            return self.login(request, *args, **kwargs)
        except ApplicationError:
            # ApplicationError関連はカスタムエラー処理が設定されている為そのまま親へスローする
            raise
        except Exception as e:
            # その他想定外エラーの場合もAPIエラーとする
            raise ApplicationError() from e
    
    def login(self, request, *args, **kwargs):
        """
        ログイン処理
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
        login_serializer = LoginSerializer(data=request.data)
        login_serializer.is_valid(raise_exception=True)
        # IPアドレスの取得 (プロキシ考慮)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        # User-Agentの取得
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        # 3. ログイン(サービス実行)
        result = self.account_service.login(
            date_now=date_now,
            kino_id=KINO_ID,
            ip_address=ip_address,
            user_agent=user_agent,
            **login_serializer.validated_data
        )
        response_param = {
            "access_token": str(result["access_token"]),
            "executeAt": date_to_str(target_date=date_now, target_format="%Y/%m/%d %H:%M:%S"),
        }
        # 4. レスポンス作成(HttpOnlyCookieへのリフレッシュトークン情報の保存)
        res = Response(response_param, status=status.HTTP_200_OK)
        try:
            res.delete_cookie("refresh_token")
        except Exception as e:
            pass
        # HttpOnlyのCookieヘッダーにTokenのセットを行う
        res.set_cookie(
            "refresh_token",
            str(result["refresh_token"]),
            max_age=60 * 60 * 24 * 30,
            httponly=True,
        )
        # 5. 処理終了ログ出力(アプリケーションログ)
        log_output_by_msg_id(log_id="MSGI004", params=[KINO_ID, str(response_param)], logger_name=LOG_METHOD.APPLICATION.value)
        # 6. レスポンス返却
        return Response(response_param, status=status.HTTP_200_OK)
