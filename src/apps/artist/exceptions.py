from rest_framework import status

# --- コアモジュール ---
from core.exceptions.exceptions import ApplicationError

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

# --------------------------------------------------
# 外部連携系 (502, 503)
# --------------------------------------------------
