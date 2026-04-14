import pytest
from apps.artist.services.artist_service import ArtistService
from apps.artist.models import T_Artist
from .factories import ArtistFactory, ArtistTagFactory, ArtistContextFactory

@pytest.mark.django_db
class TestArtistService:
    @pytest.fixture
    def service(self):
        return ArtistService()

    def test_create_artist_success(self, service, mocker):
        """アーティスト新規登録の正常系テスト"""
        user = ArtistFactory().user # UserFactoryを内包
        context = ArtistContextFactory()
        tags = [ArtistTagFactory(), ArtistTagFactory()]
        
        validated_data = {
            "spotify_id": "new_spotify_id",
            "name": "Test Artist",
            "image_url": "https://example.com/img.jpg",
            "context_id": context, # PrimaryKeyRelatedFieldによりインスタンスで渡る
            "tag_ids": tags,
            "genres": ["Rock", "J-Pop"]
        }

        artist = service.create_artist(
            user=user,
            validated_data=validated_data,
            kino_id="test_create"
        )

        assert T_Artist.objects.filter(spotify_id="new_spotify_id").exists()
        assert artist.name == "Test Artist"
        assert artist.tags.count() == 2
        assert artist.spotify_image.external_url == "https://example.com/img.jpg"

    def test_refresh_artist_single_success(self, service, mocker):
        """Spotifyからの単件リフレッシュテスト（モック利用）"""
        artist = ArtistFactory(name="Old Name")
        
        # Spotify APIのレスポンスをモック
        mock_data = {
            "id": artist.spotify_id,
            "name": "New Name",
            "genres": ["Jazz"],
            "images": [{"url": "https://newurl.com/i.jpg"}]
        }
        mocker.patch('apps.common.services.spotify_service.SpotifyService.get_artist', return_value=mock_data)

        updated_artist = service.refresh_artist_single(
            user=artist.user,
            artist_instance=artist,
            kino_id="test_refresh"
        )

        assert updated_artist.name == "New Name"
        assert updated_artist.spotify_image.external_url == "https://newurl.com/i.jpg"


import pytest
from apps.artist.services.artist_service import ArtistService
from .factories import ArtistFactory, UserFactory

@pytest.mark.django_db
class TestArtistServiceSpotifyLink:
    def test_search_artist_spotify_with_registration_flag(self, mocker):
        """Spotify検索結果にDB登録済みフラグが正しく付与されるか"""
        user = UserFactory()
        service = ArtistService()
        
        # 1. すでにDBに1件登録しておく
        registered_artist = ArtistFactory(user=user, spotify_id="id_already_exists")
        
        # 2. SpotifyServiceの検索結果をモック
        mock_spotify_results = [
            {'id': 'id_already_exists', 'name': 'Registered Artist', 'images': [], 'genres': []},
            {'id': 'id_new', 'name': 'New Artist', 'images': [], 'genres': []}
        ]
        mocker.patch(
            'apps.common.services.spotify_service.SpotifyService.fetch_search_artists',
            return_value=mock_spotify_results
        )

        # 実行
        results = service.search_artist_spotify(user=user, query="test", limit=20)

        # 検証
        assert len(results) == 2
        # 登録済みのものは is_registered が True
        assert results[0]['spotify_id'] == "id_already_exists"
        assert results[0]['is_registered'] is True
        # 未登録のものは False
        assert results[1]['spotify_id'] == "id_new"
        assert results[1]['is_registered'] is False