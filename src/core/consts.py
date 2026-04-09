from enum import Enum
from typing import List


# ログレベル
class LOG_LEVEL(Enum):
    """ロギング処理で使用するログレベルの定義"""

    DEBUG = 1
    INFO = 2
    WARNING = 3
    ERROR = 4
    FATAL = 5

    @classmethod
    def get_values(cls) -> List[int]:
        """定義されている全ての値（数値）をリストで返す"""
        return [i.value for i in cls]


# ログメソッド
class LOG_METHOD(Enum):
    """ログを出力するロガー（ロギングメソッド）の定義"""

    APPLICATION = "logger_application"
    ACCESS = "logger_access"

    @classmethod
    def get_values(cls) -> List[str]:
        """定義されている全ての値（ロガー名）をリストで返す"""
        return [i.value for i in cls]


# --- その他の定数（今後追加される可能性のあるもの）---

# ユーザー権限レベルなど...
# class USER_ROLE(Enum):
#     ADMIN = 10
#     GENERAL = 20

# アップロード関連の定数など...
# MAX_FILE_SIZE_MB = 10
