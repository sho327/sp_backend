import pytest
from apps.artist.services import ArtistService
from apps.artist.tests.factories import ArtistFactory, ArtistContextFactory
from apps.artist.exceptions import SpotifyLinkageError

@pytest.mark.django_db
class TestArtistService:
    def test_get_refreshed_artist_success(self, mocker):
        """Spotify APIから最新情報を取得してDBが更新されるか"""
        artist = ArtistFactory(name="Old Name")
        service = ArtistService()

        # Spotify APIの戻り値をモック化
        mock_data = {
            'id': artist.spotify_id,
            'name': 'New Artist Name',
            'genres': ['Pop'],
            'images': [{'url': 'http://example.com/new_image.jpg'}]
        }
        mocker.patch.object(service.spotify_service, 'fetch_artist_detail', return_value=mock_data)

        updated_artist = service.get_refreshed_artist(artist, kino_id="test_refresh")

        assert updated_artist.name == "New Artist Name"
        assert updated_artist.genres == ["Pop"]
        assert updated_artist.spotify_image.external_url == "http://example.com/new_image.jpg"

    def test_get_refreshed_artist_spotify_error(self, mocker):
        """Spotify APIがエラーを返した時に独自例外がスローされるか"""
        from core.exceptions.exceptions import ExternalServiceError
        artist = ArtistFactory()
        service = ArtistService()

        # 外部サービスエラーを模倣
        mocker.patch.object(service.spotify_service, 'fetch_artist_detail', side_effect=ExternalServiceError)

        with pytest.raises(SpotifyLinkageError):
            service.get_refreshed_artist(artist, kino_id="test_error")