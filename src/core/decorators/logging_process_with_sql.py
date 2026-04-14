import time
import json
from functools import wraps
from typing import Any, Callable, List, Tuple

from django.conf import settings
from django.db import connection
from rest_framework.request import Request
from django.core.files.base import File

from core.consts import LOG_METHOD
from core.utils.log_helpers import log_output_by_msg_id

def logging_process_with_sql(func: Callable) -> Callable:
    """
    処理中に発行されたSQLを一貫した形式でロギングするデコレータ。
    引数なしで「@logging_process_with_sql」として使用可能。
    """

    class QueryLogger:
        def __init__(self):
            self.queries: List[Tuple[str, Any]] = []

        def __call__(self, execute: Callable, sql: str, params: Any, many: bool, context: Any) -> Any:
            self.queries.append((sql, params))
            return execute(sql, params, many, context)

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # 1. クラス名と関数の特定（ログの識別用）
        instance = args[0] if args and hasattr(args[0], "__class__") else None
        class_name = instance.__class__.__name__ if instance else "Function"
        
        # Requestオブジェクトからパラメータを取得（開始ログ用）
        request = next((arg for arg in args if isinstance(arg, Request)), None)

        # 2. パラメータの抽出と加工
        log_params = {}
        if request:
            raw_data = request.data if request.method in ['POST', 'PUT', 'PATCH'] else request.query_params.dict()
            if isinstance(raw_data, (dict, list)) or hasattr(raw_data, 'items'):
                # 辞書型の場合のみ加工処理
                if hasattr(raw_data, 'items'):
                    for k, v in raw_data.items():
                        if k.lower() in ['password', 'token', 'secret', 'access_token']:
                            log_params[k] = "********"
                        elif isinstance(v, File) or hasattr(v, 'read'):
                            log_params[k] = f"<{v.__class__.__name__}: {getattr(v, 'name', 'unknown')}>"
                        else:
                            log_params[k] = v
                else:
                    log_params = raw_data
            else:
                log_params = str(raw_data)

        # 3. 処理開始ログ（ここだけ残す）
        log_output_by_msg_id(
            log_id="MSGI001",
            params=[f"[PROCESS START] {class_name}.{func.__name__} | Input: {json.dumps(log_params, ensure_ascii=False)}"],
            logger_name=LOG_METHOD.APPLICATION.value,
        )

        query_logger = QueryLogger()

        # 4. 実行とSQLキャプチャ
        try:
            if not settings.DEBUG:
                result = func(*args, **kwargs)
            else:
                with connection.execute_wrapper(query_logger):
                    result = func(*args, **kwargs)
                
                # SQL詳細ログの出力（DEBUG時のみ）
                for sql, sql_params in query_logger.queries:
                    log_output_by_msg_id(
                        log_id="MSGI001",
                        params=[f"[SQL] {sql} | Params: {sql_params}"],
                        logger_name=LOG_METHOD.APPLICATION.value,
                    )
            return result
        except Exception:
            raise

    return wrapper