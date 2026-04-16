from rest_framework import status

# --- コアモジュール ---
from core.exceptions.exceptions import ApplicationError, ExternalServiceError


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


class PlaylistAlreadyExistsError(PlaylistError):
    """同名プレイリストなどの重複エラー"""
    status_code = status.HTTP_409_CONFLICT
    message_id = "ERR_PLY_103"
    message = "Playlist Already Exists Error"
    detail = "同じ名前のプレイリストが既に存在します。"


class PlaylistCreateError(PlaylistError):
    """プレイリスト作成失敗"""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    message_id = "ERR_PLY_104"
    message = "Playlist Create Error"
    detail = "プレイリストの作成に失敗しました。"


class PlaylistReplaceError(PlaylistError):
    """トラック差し替え失敗"""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    message_id = "ERR_PLY_105"
    message = "Playlist Replace Error"
    detail = "プレイリストの曲差し替えに失敗しました。"


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

# --------------------------------------------------
# 外部連携系 (502, 503)
# --------------------------------------------------

class PlaylistExternalServiceError(ExternalServiceError):
    """Spotify / setlist.fm などの外部連携失敗時に発生"""
    status_code = status.HTTP_502_BAD_GATEWAY
    message_id = "ERR_PLY_201"
    message = "Playlist External Service Error"
    detail = "外部サービス連携に失敗しました。"