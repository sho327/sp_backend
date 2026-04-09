import pytest
from django.urls import reverse
from rest_framework import status
from apps.artist.tests.factories import ArtistFactory, ArtistTagFactory, ArtistContextFactory
from rest_framework.test import APIClient

@pytest.mark.django_db
class TestModelTArtistViewSet:
    @pytest.fixture
    def api_client(self, mocker):
        """DRFのAPIClientを使用して認証済みクライアントを返す"""
        from apps.account.tests.factories import UserFactory
        user = UserFactory()
        
        client = APIClient() # DRFのClientを生成
        client.force_authenticate(user=user)
        return client

    def test_list_artists(self, api_client):
        """一覧取得のテスト"""
        # 自分のアーティストを2件作成
        profile = api_client.handler._force_user.user_t_profile_set
        ArtistFactory.create_batch(2, user=profile)
        
        url = reverse('artist:model-t_artist-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

    def test_create_artist_with_tags(self, api_client, mocker):
        """アーティスト登録（タグ紐付けあり）のテスト"""
        tag = ArtistTagFactory()
        context = ArtistContextFactory()
        url = reverse('artist:model-t_artist-list')

        data = {
            "spotify_id": "new_spotify_id",
            "name": "Target Artist",
            "image_url": "http://image.com/test.jpg",
            "genres": ["Rock"],
            "context_id": str(context.id),
            "tag_ids": [str(tag.id)]
        }

        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == "Target Artist"
        # ManyToManyリレーション(タグ)が作成されているか確認
        from apps.artist.models import T_Artist
        assert T_Artist.objects.get(spotify_id="new_spotify_id").tags.count() == 1

    def test_search_spotify(self, api_client, mocker):
        """Spotify検索APIのテスト"""
        url = reverse('artist:model_t_artist_search-spotify')
        
        # Spotifyの検索結果をモック
        mock_search_results = [{
            'id': 'sp_1',
            'name': 'Artist A',
            'images': [{'url': 'http://img.jpg'}],
            'genres': ['Jazz'],
            'popularity': 80
        }]
        # ArtistService内のspotify_serviceをモック
        mocker.patch('apps.artist.services.SpotifyService.search_artists', return_value=mock_search_results)

        response = api_client.get(url, {'q': 'Artist A'})

        assert response.status_code == status.HTTP_200_OK
        assert response.data[0]['spotify_id'] == 'sp_1'
        assert response.data[0]['is_registered'] is False