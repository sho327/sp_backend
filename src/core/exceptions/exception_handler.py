from datetime import datetime
from rest_framework.views import exception_handler
from rest_framework import status
from core.consts import LOG_METHOD
from core.utils.log_helpers import log_output_by_msg_id
from core.exceptions.exceptions import ApplicationError

def custom_exception_handler(exc, context):
    """
    カスタム例外ハンドラの定義
    """
    # DRFの標準ハンドラを呼び出し、デフォルトのレスポンスを取得
    response = exception_handler(exc, context)

    # 1. DRFが扱えない例外(Python標準例外など)の場合、500エラーとして返却する
    if response is None:
        log_output_by_msg_id(
            log_id="MSGE002",
            params=["System Error", str(exc), "Unexpected Python Exception"],
            logger_name=LOG_METHOD.APPLICATION.value,
        )
        return None

    # 2. 共通レスポンスフォーマットの構築
    # response.data を一旦退避(ValidationError等はここが辞書になっている)
    original_data = response.data
    
    formatted_data = {
        "status_code": str(response.status_code),
        "message": "Error",
        "message_id": "ERR_STANDARD",
        "description": original_data,
        "path": context["request"].path if "request" in context else None,
        "executeAt": datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    }

    # 3. ApplicationError(自作例外)の場合の特別処理
    if isinstance(exc, ApplicationError):
        formatted_data["message"] = exc.message
        formatted_data["message_id"] = exc.message_id
        # descriptionは__init__で渡した detail (exc.detail) を使う
        formatted_data["description"] = str(exc.detail)
    
    # 4. ValidationError(DRF標準)の場合の微調整
    # ※このルートは基本的に使用されない(view側でtry/exceptで囲む)
    # elif response.status_code == status.HTTP_400_BAD_REQUEST:
    #     formatted_data["message"] = "入力内容に誤りがあります。"
    #     formatted_data["message_id"] = "ERR_VALIDATION"

    # 最終的なデータをresponse.dataにセット
    response.data = formatted_data

    # 5. ログ出力
    log_output_by_msg_id(
        log_id="MSGE002",
        params=[
            response.data.get("message_id", ""),
            str(response.data.get("description", "")),
            str(response.data),
        ],
        logger_name=LOG_METHOD.APPLICATION.value,
    )

    return response
