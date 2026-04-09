import logging
import traceback

from django.conf import settings

from core import consts, messages


def log_output_by_msg_id(
    log_id: str,
    params: list = [],
    logger_name: str = consts.LOG_METHOD.APPLICATION.value,
    exc_info: bool = False,
):
    """
    メッセージIDとパラメータからメッセージを取得し、対応するロガーに出力するヘルパー関数。
    """

    # 1. ロガーの取得
    logger = logging.getLogger(logger_name)

    # 2. メッセージの取得
    message_content = messages.get_message(log_id, params)

    # 3. ログレベルの判定
    # MSGI001 -> INFO, MSGE001 -> ERROR, MSGD001 -> DEBUG などの規則を利用
    log_prefix = log_id[:4]

    # MSGE（エラー）以上の場合は、明示的に指定がなくても
    # 実行中の例外があればスタックトレースを出すように設定
    if log_prefix in ["MSGE", "MSGF"]:
        # もし現在例外が発生している（sys.exc_infoがある）なら出す
        exc_info = True

    if log_prefix == "MSGD":
        logger.debug(message_content)
    elif log_prefix == "MSGI":
        logger.info(message_content)
    elif log_prefix == "MSGW":
        logger.warning(message_content)
    elif log_prefix == "MSGE":
        # exc_info=True にするだけで、loggingモジュールが勝手に
        # メッセージの後にスタックトレースをくっつけてくれます
        logger.error(message_content, exc_info=exc_info)
    elif log_prefix == "MSGF":
        logger.critical(message_content, exc_info=exc_info)
