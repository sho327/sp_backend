from typing import Optional, Tuple

import jwt
from django.conf import settings
from django.utils.translation import gettext_lazy as _

# --- 共通モジュール ---
from lib import consts, modules
from lib.message import MessageDefinition as md
from rest_framework.request import Request
from rest_framework_simplejwt.authentication import (
    AuthUser,
    JWTAuthentication,
    api_settings,
)
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken
from rest_framework_simplejwt.tokens import Token
from rest_framework_simplejwt.utils import get_md5_hash_password


class JwtAuthBackend(JWTAuthentication):
    def authenticate(self, request: Request) -> Optional[Tuple[AuthUser, Token]]:
        """
        Cookieに保持しているトークンを対象のヘッダー属性にセットして、デフォルトの認証処理を実行させる
        """
        # Cookieヘッダーからaccess_tokenを取得
        access_token = request.COOKIES.get("access_token")
        if not access_token:
            raise AuthenticationFailed(
                _("AccessToken not found"), code="access_token_not_found"
            )
        if access_token:
            request.META["HTTP_AUTHORIZATION"] = "{header_type} {access_token}".format(
                header_type=settings.SIMPLE_JWT["AUTH_HEADER_TYPES"][0],
                access_token=access_token,
            )
        return super().authenticate(request)

    def get_user(self, validated_token: Token) -> AuthUser:
        """
        Attempts to find and return a user using the given validated token.
        """
        try:
            user_id = validated_token[api_settings.USER_ID_CLAIM]
        except KeyError:
            raise InvalidToken(_("Token contained no recognizable user identification"))

        data = {api_settings.USER_ID_FIELD: user_id}
        # SQL実行/SELECTログ出力(アプリケーションログ)
        modules.LogOutput.log_output(
            consts.LOG_LEVEL.INFO.value,
            md.get_message(
                "MSGI005", ["jwt_authenticate/Get取得(UserModel):" + str(data)]
            ),
        )
        try:
            user = self.user_model.objects.get(**data)
        except self.user_model.DoesNotExist:
            raise AuthenticationFailed(_("User not found"), code="user_not_found")

        if not user.is_active:
            raise AuthenticationFailed(_("User is inactive"), code="user_inactive")

        if api_settings.CHECK_REVOKE_TOKEN:
            if validated_token.get(
                api_settings.REVOKE_TOKEN_CLAIM
            ) != get_md5_hash_password(user.password):
                raise AuthenticationFailed(
                    _("The user's password has been changed."), code="password_changed"
                )

        return user
