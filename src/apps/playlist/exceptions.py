from rest_framework import status

# --- コアモジュール ---
from core.exceptions.exceptions import ApplicationError


class PlaylistError(ApplicationError):
    """
    プレイリスト(Playlist)ドメインにおける全てのビジネス例外の基底クラス。
    """
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    message_id = "ERR_PLY_000"
    message = "Playlist Error"
    detail = "プレイリスト処理でエラーが発生しました。"


# --------------------------------------------------
# 参照・整合性系 (404, 400)
# --------------------------------------------------

class PlaylistNotFoundError(PlaylistError):
    """指定されたプレイリストが見つからない場合に発生"""
    status_code = status.HTTP_404_NOT_FOUND
    message_id = "ERR_PLY_101"
    message = "Playlist Not Found Error"
    detail = "指定されたプレイリストが見つかりません。"


class InvalidPlaylistRequestError(PlaylistError):
    """リクエストパラメータが業務上不正な場合に発生"""
    status_code = status.HTTP_400_BAD_REQUEST
    message_id = "ERR_PLY_102"
    message = "Invalid Playlist Request Error"
    detail = "プレイリスト操作のリクエスト内容が不正です。"


# --------------------------------------------------
# 権限・制限系 (403, 400)
# --------------------------------------------------

class PlaylistPermissionError(PlaylistError):
    """他人のプレイリストを操作しようとした場合に発生"""
    status_code = status.HTTP_403_FORBIDDEN
    message_id = "ERR_PLY_106"
    message = "Playlist Permission Error"
    detail = "このプレイリストを操作する権限がありません。"


class PlaylistTrackLimitError(PlaylistError):
    """1つのプレイリスト内の曲数制限に達した場合"""
    status_code = status.HTTP_400_BAD_REQUEST
    message_id = "ERR_PLY_107"
    message = "Playlist Track Limit Error"
    detail = "プレイリストに登録できる最大曲数に達しています。"


class PlaylistTrackNotFoundError(PlaylistError):
    """トラックが見つからない場合(404の細分化)"""
    status_code = status.HTTP_404_NOT_FOUND
    message_id = "ERR_PLY_108"
    message = "Playlist Track Not Found Error"
    detail = "指定されたトラックが存在しないか、既に削除されています。"

class PlaylistTrackAlreadyExistsError(PlaylistError):
    """プレイリストに既に同一のトラックが存在する場合に発生"""
    status_code = status.HTTP_409_CONFLICT
    message_id = "ERR_PLY_109"
    message = "Playlist Track Already Exists Error"
    detail = "このトラックは既にプレイリストに追加されています。"