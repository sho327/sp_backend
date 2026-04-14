import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from .factories import ArtistFactory, UserFactory

@pytest.mark.django_db
class TestArtistListView:
    @pytest.fixture
    def api_client(self):
        return APIClient()

    @pytest.fixture
    def auth_user(self, api_client):
        user = UserFactory()
        api_client.force_authenticate(user=user)
        return user

    def test_artist_list_success(self, api_client, auth_user):
        """一覧取得APIの正常系"""
        # 自分のアーティストを3件作成
        ArtistFactory.create_batch(3, user=auth_user)
        # 他人のアーティストを1件作成（これは出ないはず）
        ArtistFactory()

        url = reverse('artist:artist_list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 3
        assert "results" in response.data
        # MiniSerializerによりurlが含まれているか
        assert "url" in response.data["results"][0]["image_url_data"]

    def test_artist_search_spotify_api_error(self, api_client, auth_user, mocker):
        """Spotify APIエラー時の例外ハンドリングテスト"""
        from core.exceptions.exceptions import ExternalServiceError
        
        # Serviceの検索メソッドがExternalServiceErrorを投げるようモック
        mocker.patch(
            'apps.artist.services.artist_service.ArtistService.search_artist_spotify',
            side_effect=ExternalServiceError()
        )

        url = reverse('artist:artist_search')
        response = api_client.get(url, {"q": "SomeArtist"})

        # CommonResponseMixinにより、システムエラー(502等)が返ることを確認
        assert response.status_code == status.HTTP_502_BAD_GATEWAY