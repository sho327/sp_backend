import pytest
from spotipy.exceptions import SpotifyException
from apps.common.services.spotify_service import SpotifyService
from apps.common.exceptions import SpotifyAuthFailedException
from .factories import SpotifyUserTokenFactory

@pytest.mark.django_db
class TestSpotifyService:
    @pytest.fixture
    def mock_sp(self, mocker):
        """Spotipyクライアントのモック"""
        return mocker.patch('spotipy.Spotify')

    def test_fetch_get_track_success(self, mock_sp, mocker):
        """トラック取得の正常系テスト"""
        # トークン準備
        token = SpotifyUserTokenFactory()
        # APIレスポンスのモック
        mock_sp.return_value.track.return_value = {'id': 'track1', 'name': 'Song A'}
        
        service = SpotifyService(email=token.email)
        result = service.fetch_get_track('track1')
        
        assert result['name'] == 'Song A'
        mock_sp.return_value.track.assert_called_once_with('track1')

    def test_fetch_get_recommendations_params(self, mock_sp):
        """レコメンデーションの引数とリミット制限のテスト"""
        token = SpotifyUserTokenFactory()
        service = SpotifyService(email=token.email)
        
        # limitが100を超える場合の安全装置チェック
        service.fetch_get_recommendations(seed_artists=['id'], limit=150)
        
        # 内部で call_api 経由で spotipy.recommendations が呼ばれる
        # limitが100に丸められていることを検証
        mock_sp.return_value.recommendations.assert_called_once_with(
            seed_artists=['id'],
            seed_genres=None,
            seed_tracks=None,
            limit=100
        )

    def test_create_spotify_tracksets_encoding(self):
        """URL生成ロジックの検証（純粋関数）"""
        ids = ["id1", "id2"]
        urls = SpotifyService.create_spotify_tracksets(ids, title="Test List", chunk_size=1)
        
        assert len(urls) == 2
        # スペースがエンコードされているか
        assert "Test%20List" in urls[0]
        # IDが正しく結合されているか
        assert "id1" in urls[0]
        assert "id2" in urls[1]