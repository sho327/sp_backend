import os
import django
import sys
from unittest.mock import MagicMock
from datetime import datetime

# Django環境のセットアップ
sys.path.append('/Users/shogokato/test/my_sample_stb_zip/src')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def run_verification():
    from apps.playlist.services import PlaylistService
    
    # 依存関係をモック
    service = PlaylistService()
    service.spotify_service = MagicMock()
    service.setlist_service = MagicMock()
    
    # ダミーデータ
    mock_artist = MagicMock()
    mock_artist.spotify_id = "artist_id_1"
    mock_artist.name = "Artist 1"
    
    user = MagicMock()
    
    base_data = {
        "pattern": "top_tracks",
        "get_tracks_count": 2,
        "artist_ids": [mock_artist],
        "mood_brightness": 70,
        "mood_intensity": 30
    }

    # Pattern: top_tracks
    service.spotify_service.fetch_get_artist_top_tracks.return_value = [
        {"id": "t1", "name": "Top 1"},
        {"id": "t2", "name": "Top 2"}
    ]
    tracks = service.generate_playlist_tracks(datetime.now(), "web", user, base_data)
    print(f"top_tracks: {len(tracks)}")
    assert len(tracks) == 2
    assert tracks[0]["name"] == "Top 1"

    # Pattern: set_list
    base_data["pattern"] = "set_list"
    service.setlist_service.get_latest_setlist_song_names.return_value = ["Song 1", "Song 2"]
    service.spotify_service.fetch_search_tracks.side_effect = lambda q, limit: [{"id": "sid", "name": "SName"}]
    tracks = service.generate_playlist_tracks(datetime.now(), "web", user, base_data)
    print(f"set_list: {len(tracks)}")
    assert len(tracks) == 2

    # Pattern: moodfilter
    base_data["pattern"] = "moodfilter"
    service.spotify_service.fetch_get_recommendations.return_value = [{"id": "r1", "name": "Rec 1"}]
    tracks = service.generate_playlist_tracks(datetime.now(), "web", user, base_data)
    print(f"moodfilter: {len(tracks)}")
    assert len(tracks) == 1
    service.spotify_service.fetch_get_recommendations.assert_called_with(
        seed_artists=["artist_id_1"],
        limit=2,
        target_valence=0.7,
        target_energy=0.3
    )

    print("\nVerification Successful!")

if __name__ == "__main__":
    run_verification()
