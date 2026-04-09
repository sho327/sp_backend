import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import authentication, exceptions

User = get_user_model()


class SupabaseJwtAuthBackend(authentication.BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        if not auth_header:
            return None

        try:
            # "Bearer <token>" の形式からトークンを抽出
            token = auth_header.split(" ")[1]
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience=settings.SUPABASE_AUDIENCE,
            )
        except Exception:
            raise exceptions.AuthenticationFailed("Invalid token")

        # Supabaseの 'sub' (UUID) を取得
        supabase_user_id = payload.get("sub")

        # Django側のユーザーモデルと紐付け
        # Djangoで管理しているユーザに supabase_user_id フィールドを持たせているので比較
        try:
            user = User.objects.get(supabase_user_id=supabase_user_id)
        except User.DoesNotExist:
            # 必要に応じてここでDjango側にもユーザーを自動作成する（JITプロビジョニング）
            raise exceptions.AuthenticationFailed("User not found in Django")

        return (user, None)
