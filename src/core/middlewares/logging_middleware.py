import time
from typing import Callable, Optional

from django.http import HttpRequest, HttpResponse

# --- コアモジュール ---
from core.consts import LOG_METHOD
from core.utils.common import set_str_or_none_format
from core.utils.log_helpers import log_output_by_msg_id

"""
リクエスト/レスポンスをロギングするミドルウェア
"""


class LoggingMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

        # サービス開始ログ出力 (アプリケーションログ)
        log_output_by_msg_id(
            log_id="MSGI002",
            logger_name=LOG_METHOD.APPLICATION.value,
        )

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # リクエスト開始時間
        t0 = time.time()

        # クライアント情報
        client_ip = get_client_ip(request)
        client_host = set_str_or_none_format(request.META.get("REMOTE_HOST"))
        http_host = set_str_or_none_format(request.META.get("HTTP_HOST"))

        # サーバ情報
        server_name = set_str_or_none_format(request.META.get("SERVER_NAME"))
        server_port = set_str_or_none_format(request.META.get("SERVER_PORT"))

        # リクエスト情報
        request_method = request.method
        path = request.path
        content_length = set_str_or_none_format(request.META.get("CONTENT_LENGTH"))
        content_type = set_str_or_none_format(request.META.get("CONTENT_TYPE"))

        # レスポンスの取得
        response = self.get_response(request)

        # レスポンス情報
        status_code = response.status_code
        t1 = time.time()

        # メッセージ内容の設定
        message = (
            f"{client_ip} {client_host} {http_host} -> {server_name} {server_port} "
            f"{request_method} {path} {status_code} {content_type} "
            f"size: {content_length} time: {t1 - t0:.4f}"  # 処理時間を小数点以下4桁でフォーマット
        )

        # ステータスコードの判定（200番台はINFO、それ以外はWARNING）
        if 200 <= status_code < 300:
            log_id_to_use = "MSGI001"  # 汎用INFOメッセージID
        else:
            log_id_to_use = "MSGW001"  # 汎用WARNINGメッセージID

        log_output_by_msg_id(
            log_id=log_id_to_use,
            params=[message],
            logger_name=LOG_METHOD.ACCESS.value,
        )

        return response


def get_client_ip(request: HttpRequest) -> Optional[str]:
    """
    クライアントのIPアドレスを取得 (HTTP_X_FORWARDED_FORに対応)
    """
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        # 複数のIPがある場合、最初のIP（クライアントのIP）を取得
        ip = x_forwarded_for.split(",")[0]
    else:
        # プロキシがない場合のIPを取得
        ip = request.META.get("REMOTE_ADDR")

    return ip
