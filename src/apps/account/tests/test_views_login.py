import pytest
from django.urls import reverse
from django.test import override_settings
from django.conf import settings
from rest_framework import status
from apps.account.models import M_User, T_Profile, T_LoginHistory
from apps.account.tests.factories import UserFactory

@pytest.mark.django_db(transaction=True)
class TestLoginView:
    @pytest.fixture
    def login_url(self):
        return reverse('account:login')

    def test_login_success(self, client, login_url, mocker):
        """正常なログインテスト（Cookieセット関数の呼び出しを検証）"""
        # DjangoのレスポンスオブジェクトがCookieをセットするメソッドを監視
        from django.http import HttpResponseBase
        spy_set_cookie = mocker.spy(HttpResponseBase, 'set_cookie')

        password = "correct_password"
        user = UserFactory(password=password, is_active=True)

        data = {"email": user.email, "password": password}
        response = client.post(login_url, data, content_type="application/json")

        # ステータスとデータの確認
        assert response.status_code == status.HTTP_200_OK
        assert "access_token" in response.data

        # Cookieがセットされたか「呼び出し履歴」で確認
        # 第一引数(self)は任意、第二引数にキー名が入っているか
        spy_set_cookie.assert_any_call(
            mocker.ANY, 
            "refresh_token", 
            mocker.ANY, 
            max_age=mocker.ANY, 
            httponly=True
        )

    def test_login_failure_invalid_password(self, client, login_url):
        """パスワード間違い時のテスト"""
        user = UserFactory(password="correct_password", is_active=True)
        data = {"email": user.email, "password": "wrong_password"}
        
        response = client.post(login_url, data, content_type="application/json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        
        # 失敗履歴の確認
        history = T_LoginHistory.objects.filter(login_identifier=user.email).last()
        assert history.is_successful is False
        assert history.failure_reason == T_LoginHistory.FailureReason.PASSWORD_MISMATCH

    def test_login_lockout_after_5_failures(self, client, login_url):
        """5回失敗後のアカウントロックテスト"""
        user = UserFactory(password="correct_password", is_active=True)
        data = {"email": user.email, "password": "wrong_password"}

        # 5回失敗させる
        for _ in range(5):
            client.post(login_url, data, content_type="application/json")

        # プロフィールが一時ロック状態になっているか確認
        profile = T_Profile.objects.get(user=user)
        assert profile.status_code == T_Profile.AccountStatus.TEMPORARY_LOCKED
        assert profile.locked_until_at is not None

        # 6回目の試行はロックエラーになるはず
        user.refresh_from_db()
        response = client.post(login_url, data, content_type="application/json")
        # サービス内でAccountLockedErrorが投げられ、ApplicationErrorとして返る想定
        assert response.status_code == status.HTTP_403_FORBIDDEN 

    def test_login_inactive_user(self, client, login_url):
        """アクティベーション前のユーザーはログイン不可"""
        user = UserFactory(password="password", is_active=False)
        data = {"email": user.email, "password": "password"}
        
        response = client.post(login_url, data, content_type="application/json")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        history = T_LoginHistory.objects.filter(user=user).last()
        assert history.failure_reason == T_LoginHistory.FailureReason.NOT_ACTIVATED