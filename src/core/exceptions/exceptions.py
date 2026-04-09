from rest_framework import status
from rest_framework.exceptions import APIException


class ApplicationError(APIException):
    """
    全てのカスタムビジネス例外の基底クラス。
    業務ロジックで発生したエラー情報を統一的に保持し、
    プレゼンテーション層での処理を容易にする。
    """

    # --------------------------------------------------
    # 共通属性 (子クラスで上書きされることを想定)
    # --------------------------------------------------

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    message_id = "ERR_UNKNOWN"
    message = "Internal Server Error"
    detail = "予期せぬエラーが発生しました。"

    def __init__(self, message=None, message_id=None):
        # detailが未指定ならデフォルトメッセージを入れるなどの調整
        super().__init__(detail=self.detail)
        # メッセージがあれば上書き、なければクラスのデフォルト
        if message_id:
            self.message_id = message_id


# --------------------------------------------------
# 認証・権限系 (401, 403)
# --------------------------------------------------


class AuthenticationFailedError(ApplicationError):
    """認証に失敗した場合（ログイン情報の誤りなど）"""

    status_code = status.HTTP_401_UNAUTHORIZED
    message_id = "ERR_AUTH_001"
    message = "Authentication Failed Error"
    detail = "認証に失敗しました。"


class PermissionDeniedError(ApplicationError):
    """権限が不足している場合"""

    status_code = status.HTTP_403_FORBIDDEN
    message_id = "ERR_AUTH_002"
    message = "Permission Denied Error"
    detail = "この操作を実行する権限がありません。"


# --------------------------------------------------
# リソース操作系 (400, 404, 409)
# --------------------------------------------------


class ResourceNotFoundError(ApplicationError):
    """データが見つからない場合"""

    status_code = status.HTTP_404_NOT_FOUND
    message_id = "ERR_NOT_FOUND"
    message = "Resource Not Found Error"
    detail = "指定されたリソースが見つかりませんでした。"


class ValidationError(ApplicationError):
    """入力値の不備やロジック上の不正なリクエスト"""

    status_code = status.HTTP_400_BAD_REQUEST
    message_id = "ERR_VALIDATION"
    message = "Validation Error"
    detail = "入力内容に誤りがあります。"


class DuplicationError(ApplicationError):
    """一意制約違反（既に存在する場合）"""

    status_code = status.HTTP_409_CONFLICT
    message_id = "ERR_DATA_DUPLICATION"
    message = "Duplication Error"
    detail = "既に登録されている情報です。"


class IntegrityError(ApplicationError):
    """データベースの整合性問題"""

    status_code = status.HTTP_400_BAD_REQUEST
    message_id = "ERR_DB_INTEGRITY"
    message = "Integrity Error"
    detail = "データの不整合が発生しました。"


# --------------------------------------------------
# 外部・インフラ系 (500, 503)
# --------------------------------------------------


class ExternalServiceError(ApplicationError):
    """外部API連携やサードパーティサービスの失敗"""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    message_id = "ERR_EXTERNAL_SERVICE"
    message = "External Service Error"
    detail = "外部サービスとの連携に失敗しました。"


class ConfigurationError(ApplicationError):
    """設定不備などシステム側の問題"""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    message_id = "ERR_CONFIG"
    message = "Configuration Error"
    detail = "システム設定エラーが発生しました。"
