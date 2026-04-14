from rest_framework import status

# --- コアモジュール ---
from core.exceptions.exceptions import ApplicationError

class CommonError(ApplicationError):
    """
    共通（Common）ドメインにおける全てのビジネス例外の基底クラス。
    """
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    message_id = "ERR_COM_000"
    detail = "共通機能の処理中にエラーが発生しました。"

# --------------------------------------------------
# ファイルリソース系 (404, 400)
# --------------------------------------------------

class FileResourceNotFoundException(CommonError):
    """指定されたファイルリソースが見つからない場合に発生"""
    status_code = status.HTTP_404_NOT_FOUND
    message_id = "ERR_COM_101"
    detail = "指定されたファイルが見つかりません。"

class InvalidFileTypeException(CommonError):
    """許可されていないファイル形式がアップロードされた場合に発生"""
    status_code = status.HTTP_400_BAD_REQUEST
    message_id = "ERR_COM_102"
    detail = "このファイル形式はサポートされていません。"

class FileSizeLimitExceededException(CommonError):
    """ファイルサイズが制限を超えている場合に発生"""
    status_code = status.HTTP_400_BAD_REQUEST
    message_id = "ERR_COM_103"
    detail = "ファイルサイズが制限を超えています。"

class FileUploadFailedException(CommonError):
    """ファイルの書き込みやアップロード処理自体が失敗した場合"""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    message_id = "ERR_COM_104"
    detail = "ファイルのアップロードに失敗しました。"

# --------------------------------------------------
# Spotify接続系 (401, 404, 409, 429)
# --------------------------------------------------

class SpotifyTokenNotFoundException(CommonError):
    """DBにトークンがない場合"""
    status_code = status.HTTP_404_NOT_FOUND
    message_id = "ERR_COM_201"
    detail = "Spotify連携が設定されていません。"

class SpotifyAuthFailedException(CommonError):
    """Spotify側の認証エラー(Token無効など)"""
    status_code = status.HTTP_401_UNAUTHORIZED
    message_id = "ERR_COM_202"
    detail = "Spotifyの認証に失敗しました。再連携してください。"

class SpotifyApiLimitException(CommonError):
    """レート制限(429 Too Many Requests)"""
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    message_id = "ERR_COM_203"
    detail = "Spotify APIの利用制限を超えました。しばらく時間をおいてください。"
