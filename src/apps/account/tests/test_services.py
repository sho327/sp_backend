import pytest
from django.utils import timezone
from apps.account.services import AccountService
from apps.account.models import M_User, T_Profile, T_UserToken
from .factories import UserFactory

@pytest.mark.django_db
class TestAccountService:
    def test_account_withdraw_logical_delete(self):
        """退会処理（論理削除）のテスト"""
        service = AccountService()
        user = UserFactory(is_active=True)
        now = timezone.now()
        kino_id = "test_withdraw"

        service.account_withdraw(date_now=now, kino_id=kino_id, user_id=user.id)

        # ユーザーが非活性かつ論理削除日時が入っているか
        user.refresh_from_db()
        assert user.is_active is False
        assert user.deleted_at is not None
        
        # プロフィールも論理削除されているか
        profile = T_Profile.objects.get(user=user)
        assert profile.deleted_at is not None

    def test_create_user_token_collision_retry(self, mocker):
        """トークン衝突時のリトライロジック（モックを利用）"""
        service = AccountService()
        user = UserFactory()
        
        # 1回目だけIntegrityErrorを発生させ、2回目で成功させるシミュレーション
        from django.db import IntegrityError
        mock_create = mocker.patch('apps.account.models.T_UserToken.objects.create')
        mock_create.side_effect = [IntegrityError, None]

        token = service._create_user_token(
            user=user, 
            token_type=T_UserToken.TokenType.ACTIVATION, 
            date_now=timezone.now(), 
            kino_id="test"
        )
        
        assert token is not None
        assert mock_create.call_count == 2