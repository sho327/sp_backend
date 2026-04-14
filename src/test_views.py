import os
import django
import sys
from unittest.mock import MagicMock, patch
from datetime import datetime

# Django環境のセットアップ
sys.path.append('/Users/shogokato/test/my_sample_stb_zip/src')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def run_verification():
    from apps.playlist.views.playlist_generate import PlaylistGenerateView
    from apps.playlist.views.playlist_create import PlaylistCreateView
    from rest_framework.test import APIRequestFactory, force_authenticate
    
    factory = APIRequestFactory()
    user = MagicMock() # モックユーザー
    user.is_authenticated = True
    user.pk = 1
    
    # ダミーアーティスト
    mock_artist = MagicMock()
    mock_artist.name = "Radiohead"
    mock_artist.id = "4Z8W79mYvSGrv21ZpS0S5v"

    # 1. PlaylistGenerateView の検証
    print("--- Testing PlaylistGenerateView ---")
    generate_view = PlaylistGenerateView.as_view()
    
    # リクエストデータ
    generate_data = {
        "title": "My Generate List",
        "pattern": "top_tracks",
        "get_tracks_count": 3,
        "artist_ids": [],
        "spotify_id": "dummy"
    }
    
    # バリデーションとサービスをモック
    with patch('apps.playlist.serializer.playlist_genarate.PlaylistGenerateRequestSerializer.is_valid', return_value=True), \
         patch('apps.playlist.serializer.playlist_genarate.PlaylistGenerateRequestSerializer.validated_data', new_callable=MagicMock) as mock_val_data, \
         patch('apps.playlist.services.PlaylistService.generate_playlist_tracks', return_value=[{"name": "Song 1", "spotify_id": "s1", "artist": mock_artist}]) as mock_gen:
        
        mock_val_data.get.side_effect = lambda k, default=None: generate_data.get(k, default)
        
        request = factory.post('/api/playlist/generate/', generate_data, format='json')
        force_authenticate(request, user=user)
        response = generate_view(request)
        
        print(f"Status: {response.status_code}")
        # print(f"Data: {response.data}")
        assert response.status_code == 200
        assert "tracks" in response.data["data"]

    # 2. PlaylistCreateView の検証
    print("\n--- Testing PlaylistCreateView ---")
    create_view = PlaylistCreateView.as_view()
    
    create_data = {
        "title": "My New List",
        "spotify_id": "dummy",
        "tracks": [{"name": "Song 1", "spotify_id": "s1"}]
    }
    
    with patch('apps.playlist.serializer.playlist_create.PlaylistCreateRequestSerializer.is_valid', return_value=True), \
         patch('apps.playlist.serializer.playlist_create.PlaylistCreateRequestSerializer.validated_data', new_callable=MagicMock) as mock_val_data, \
         patch('apps.playlist.services.PlaylistService.create_playlist', return_value=MagicMock(title="My New List")) as mock_create:
        
        mock_val_data.get.side_effect = lambda k, default=None: create_data.get(k, default)
        
        request = factory.post('/api/playlist/create/', create_data, format='json')
        force_authenticate(request, user=user)
        response = create_view(request)
        
        print(f"Status: {response.status_code}")
        assert response.status_code == 200

    print("\nView Verification Successful!")

if __name__ == "__main__":
    run_verification()
