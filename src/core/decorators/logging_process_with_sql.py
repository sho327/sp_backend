import time, json, uuid
from functools import wraps
from typing import Any, Callable, List, Tuple

from django.conf import settings
from django.db import connection
from rest_framework.request import Request
from django.core.files.base import File

from core.consts import LOG_METHOD
from core.utils.log_helpers import log_output_by_msg_id

def logging_process_with_sql(process_name: str) -> Callable:
    """
    処理の開始/終了、実行時間、リクエストパラメータ、
    および発行されたSQLを一貫した形式でロギングするデコレータ。
    """

    def actual_decorator(func: Callable) -> Callable:
        
        class QueryLogger:
            def __init__(self):
                self.queries: List[Tuple[str, Any]] = []

            def __call__(self, execute: Callable, sql: str, params: Any, many: bool, context: Any) -> Any:
                self.queries.append((sql, params))
                return execute(sql, params, many, context)

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 1. クラス名とリクエストの特定
            instance = args[0] if args and hasattr(args[0], "__class__") else None
            class_name = instance.__class__.__name__ if instance else "Function"
            
            # Requestオブジェクトを探す(ViewSet/APIViewのメソッドなら通常第2引数)
            request = next((arg for arg in args if isinstance(arg, Request)), None)

            # 2. パラメータの抽出と加工(マスキング&バイナリ対策)
            log_params = {}
            if request:
                raw_data = request.data if request.method in ['POST', 'PUT', 'PATCH'] else request.query_params.dict()
                
                # データのコピーと加工
                if isinstance(raw_data, dict) or hasattr(raw_data, 'items'):
                    for k, v in raw_data.items():
                        # マスキング
                        if k.lower() in ['password', 'token', 'secret', 'access_token']:
                            log_params[k] = "********"
                        # ファイルオブジェクトの置換
                        elif isinstance(v, File) or hasattr(v, 'read'):
                            log_params[k] = f"<{v.__class__.__name__}: {getattr(v, 'name', 'unknown')}>"
                        else:
                            log_params[k] = v
                else:
                    log_params = raw_data

            # 3. 処理開始ログ
            log_output_by_msg_id(
                log_id="MSGI001",
                params=[f"[PROCESS START] {class_name}.{func.__name__} ({process_name}) | Input: {json.dumps(log_params, ensure_ascii=False)}"],
                logger_name=LOG_METHOD.APPLICATION.value,
            )

            start_time = time.perf_counter()
            query_logger = QueryLogger()

            # 4. 実行(DEBUG時のみSQLをキャプチャ)
            try:
                if not settings.DEBUG:
                    result = func(*args, **kwargs)
                else:
                    with connection.execute_wrapper(query_logger):
                        result = func(*args, **kwargs)
                    
                    # --- ヘッダーログ出力 ---
                    # log_output_by_msg_id(
                    #     log_id="MSGI001",
                    #     params=[f"=== SQL START: {class_name}.{func.__name__} ({process_name}) ==="],
                    #     logger_name=LOG_METHOD.APPLICATION.value,
                    # )
                    
                    # SQL詳細ログの出力
                    for sql, sql_params in query_logger.queries:
                        log_output_by_msg_id(
                            log_id="MSGI001",
                            params=[f"[SQL] {sql} | Params: {sql_params}"],
                            logger_name=LOG_METHOD.APPLICATION.value,
                        )
                    
                    # --- フッターログ出力 ---
                    # log_output_by_msg_id(
                    #     log_id="MSGI001",
                    #     params=[f"=== SQL END: Total Queries ({len(logger_instance.queries)}) ==="],
                    #     logger_name=LOG_METHOD.APPLICATION.value,
                    # )

            finally:
                # 5. 処理終了ログ
                execution_time = (time.perf_counter() - start_time) * 1000
                query_count = len(query_logger.queries) if settings.DEBUG else "N/A"
                log_output_by_msg_id(
                    log_id="MSGI001",
                    params=[f"[PROCESS END] {process_name} | Time: {execution_time:.2f}ms | Queries: {query_count}"],
                    logger_name=LOG_METHOD.APPLICATION.value,
                )

            return result
        return wrapper
    return actual_decorator