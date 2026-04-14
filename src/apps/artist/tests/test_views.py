@pytest.mark.django_db
class TestArtistDetailView:
    def test_artist_detail_with_refresh(self, api_client, auth_user, mocker):
        """詳細取得時にrefreshパラメータでSpotify同期が行われるか"""
        artist = ArtistFactory(user=auth_user, name="Old Name")
        
        # Spotifyからの最新データ
        mock_latest = {
            'id': artist.spotify_id,
            'name': 'New Name From Spotify',
            'genres': ['J-Pop'],
            'images': [{'url': 'http://new-image.jpg'}]
        }
        # get_artist をモック
        mocker.patch(
            'apps.common.services.spotify_service.SpotifyService.fetch_get_artist',
            return_value=mock_latest
        )

        url = reverse('artist:artist_detail', kwargs={'artist_id': artist.id})
        # ?refresh=true を付けてリクエスト
        response = api_client.get(url, {'refresh': 'true'})

        assert response.status_code == status.HTTP_200_OK
        # レスポンスが新しくなっているか
        assert response.data['name'] == 'New Name From Spotify'
        
        # DBも更新されているか
        artist.refresh_from_db()
        assert artist.name == 'New Name From Spotify'