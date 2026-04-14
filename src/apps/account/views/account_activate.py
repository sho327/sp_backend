from datetime import datetime
from django.utils import timezone
from rest_framework.permissions import AllowAny

# --- コアモジュール ---
from core.decorators.logging_process_with_sql import logging_process_with_sql
from core.consts import LOG_METHOD
from core.utils.log_helpers import log_output_by_msg_id
from core.utils.date_format import convert_to_site_timezone
from core.exceptions.exceptions import ApplicationError
from core.views import BaseAPIView

# --- アカウントモジュール ---
from apps.account.serializer.account_activate import AccountActivateRequestSerializer, AccountActivateResponseSerializer
from apps.account.services import AccountService


KINO_ID = "account-activate"

class AccountActivateView(BaseAPIView):
    """
    アカウント有効化APIクラス
    """
    permission_classes = [AllowAny]
    account_service = AccountService()

    @logging_process_with_sql
    def post(self, request, *args, **kwargs):
        """
        URLパラメータ等からトークンを受け取り、有効化を実行する
        """
        try:
            return self.account_activate(request, *args, **kwargs)
        except ApplicationError:
            # ApplicationError関連はカスタムエラー処理が設定されている為そのまま親へスローする
            raise
        except Exception as e:
            # その他想定外エラーの場合もAPIエラーとする
            raise ApplicationError() from e

    def account_activate(self, request, *args, **kwargs):
        """
        アカウント有効化処理
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
        serializer = AccountActivateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # 3. アカウントアクティベート(サービス実行)
        self.account_service.activate_user(
            date_now, 
            KINO_ID, 
            raw_token=serializer.validated_data.get("token")
        )
        # 4. レスポンス作成（ここがポイント）
        # 空であってもResponseSerializerを通す/「このAPIが何を返すか」がViewの最後を見れば一目でわかるようにする
        # data=Noneまたは空辞書を渡すことで、executeAtだけが入ったレスポンスとなる
        res_serializer = AccountActivateResponseSerializer({})
        response = self.get_success_map_response(data=res_serializer.data)
        # 4. 処理終了ログ出力(アプリケーションログ)
        log_output_by_msg_id(log_id="MSGI004", params=[KINO_ID, str(response.data)], logger_name=LOG_METHOD.APPLICATION.value)
        # 5. レスポンス返却
        return response
