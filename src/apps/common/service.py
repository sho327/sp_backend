import hashlib
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from core.utils.common import generate_secure_token

from apps.account.models import T_UserToken
User = get_user_model()

class CommonService:
    """
    共通サービスクラス
    """

    # ------------------------------------------------------------------
    # ユーザトークン作成処理
    # ------------------------------------------------------------------
    def _create_user_token(
        self, 
        user: User, 
        token_type: str, 
        kino_id: str, 
        expires_hours: int = 24
    ) -> str:
        """
        指定されたタイプのハッシュ化トークンを生成・保存し、生のトークンを返す。
        """
        # 1. 生のセキュアトークンを生成
        raw_token = generate_secure_token(32)
        
        # 2. ハッシュ化（DB保存用）
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        
        # 3. 有効期限の計算
        expires_at = timezone.now() + timezone.timedelta(hours=expires_hours)
        
        # 4. DB保存（既存の同タイプトークンを無効化する処理を入れても良い）
        with transaction.atomic():
            # 必要であれば、同じタイプの古いトークンを削除または無効化
            T_UserToken.objects.filter(
                user=user, 
                token_type=token_type
            ).delete()

            T_UserToken.objects.create(
                user=user,
                token_type=token_type,
                token_hash=token_hash,
                expired_at=expires_at,
                created_method=kino_id,
                updated_method=kino_id,
            )
            
        return raw_token
