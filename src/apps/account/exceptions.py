from rest_framework import status

# --- コアモジュール ---
from core.exceptions.exceptions import ApplicationError

class AccountError(ApplicationError):
    """
    ユーザーアカウント（Account）ドメインにおける全てのビジネス例外の基底クラス。
    """
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    message_id = "ERR_ACC_000"
    message = "Account Error"
    detail = "アカウント関連の処理中にエラーが発生しました。"

# --------------------------------------------------
# ユーザー取得・状態系 (404, 400)
# --------------------------------------------------

class UserNotFoundError(AccountError):
    """指定されたユーザーが見つからない場合に発生"""
    status_code = status.HTTP_404_NOT_FOUND
    message_id = "ERR_ACC_101"
    message = "User Not Found Error"
    detail = "指定されたユーザーアカウントが見つかりません。"

class UserAlreadyActiveError(AccountError):
    """既に有効化済みのユーザーに対して再度アクティベーションを行おうとした場合に発生"""
    status_code = status.HTTP_400_BAD_REQUEST
    message_id = "ERR_ACC_103"
    message = "User Already Active Error"
    detail = "このアカウントは既に有効化されています。"

class EmailDuplicationError(AccountError):
    """メールアドレスが既に登録されている場合に発生"""
    status_code = status.HTTP_400_BAD_REQUEST
    message_id = "ERR_ACC_104"
    message = "Email Duplication Error"
    detail = "このメールアドレスは既に登録されています。"

# --------------------------------------------------
# 認証・セキュリティ系 (401, 403)
# --------------------------------------------------

class AuthenticationFailedError(AccountError):
    """メールアドレスまたはパスワードが誤っている場合"""
    status_code = status.HTTP_401_UNAUTHORIZED
    message_id = "ERR_AUTH_001"
    message = "Authentication Failed Error"
    detail = "メールアドレスまたはパスワードが正しくありません。"

class AccountLockedError(AccountError):
    """アカウントがロックまたは凍結されている場合"""
    status_code = status.HTTP_403_FORBIDDEN
    message_id = "ERR_AUTH_002"
    message = "Account Locked Error"
    detail = "このアカウントは現在利用できません。管理者にお問い合わせください。"

# --------------------------------------------------
# トークン系 (400)
# --------------------------------------------------

class TokenExpiredOrNotFoundError(AccountError):
    """アクティベーショントークンが無効である、または期限が切れている場合に発生"""
    status_code = status.HTTP_400_BAD_REQUEST
    message_id = "ERR_ACC_102"
    message = "Token Expired Or Not Found Error"
    detail = "無効または期限切れのアクティベーション・トークンです。"

class PasswordResetTokenInvalidError(AccountError):
    """パスワードリセットトークンが無効または期限切れの場合"""
    status_code = status.HTTP_400_BAD_REQUEST
    message_id = "ERR_AUTH_003"
    message = "Password Reset Token Invalid Error"
    detail = "無効なパスワードリセットリンクです。もう一度手続きを行ってください。"
