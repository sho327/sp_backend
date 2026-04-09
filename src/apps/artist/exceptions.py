from rest_framework import status
from core.exceptions.exceptions import ApplicationError, ExternalServiceError

class ArtistError(ApplicationError):
    """
    アーティスト（Artist）ドメインにおける全てのビジネス例外の基底クラス。
    """
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    message_id = "ERR_ART_000"
    message = "Artist Error"
    detail = "アーティスト関連の処理中にエラーが発生しました。"

# --------------------------------------------------
# 登録・重複系 (400, 409)
# --------------------------------------------------

class ArtistAlreadyExistsError(ArtistError):
    """同一ユーザーが既に同じアーティスト(Spotify ID)を登録している場合に発生"""
    status_code = status.HTTP_400_BAD_REQUEST
    message_id = "ERR_ART_101"
    message = "Artist Already Exists Error"
    detail = "このアーティストは既に登録されています。"

# --------------------------------------------------
# 参照・整合性系 (404, 400)
# --------------------------------------------------

class ArtistNotFoundError(ArtistError):
    """指定されたアーティストトランが見つからない場合に発生"""
    status_code = status.HTTP_404_NOT_FOUND
    message_id = "ERR_ART_102"
    message = "Artist Not Found Error"
    detail = "指定されたアーティスト情報が見つかりません。"

class InvalidContextError(ArtistError):
    """指定されたコンテキスト(きっかけ)が無効または削除されている場合に発生"""
    status_code = status.HTTP_400_BAD_REQUEST
    message_id = "ERR_ART_103"
    message = "Invalid Context Error"
    detail = "選択されたコンテキストは無効です。"

class InvalidTagError(ArtistError):
    """指定されたタグが無効または削除されている場合に発生"""
    status_code = status.HTTP_400_BAD_REQUEST
    message_id = "ERR_ART_104"
    message = "Invalid Tag Error"
    detail = "選択されたタグの一部が無効です。"

# --------------------------------------------------
# 外部連携系 (502, 503)
# --------------------------------------------------

class SpotifyLinkageError(ExternalServiceError):
    """Spotify APIとの通信やデータ取得に失敗した場合に発生"""
    status_code = status.HTTP_502_BAD_GATEWAY
    message_id = "ERR_ART_201"
    message = "Spotify Linkage Error"
    detail = "Spotifyからのデータ取得に失敗しました。しばらく時間を置いてから再度お試しください。"