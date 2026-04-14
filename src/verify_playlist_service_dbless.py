import sys
from unittest.mock import MagicMock, patch
from datetime import datetime

# Django環境のセットアップ (インポートのみ)
sys.path.append('/Users/shogokato/test/my_sample_stb_zip/src')

# モックの作成
MockArtist = MagicMock()
MockUser = MagicMock()

def run_verification():
    # PlaylistService をインポート (ただし、内部でのDjango依存を避けるためにモックを先に設定)
    with patch('apps.common.services.spotify_service.SpotifyService'), \
         patch('apps.common.services.setlistfm_service.SetlistFmService'), \
         patch('apps.playlist.models.T_Playlist'), \
         patch('apps.playlist.models.T_PlaylistTrack'), \
         patch('apps.playlist.models.R_PlaylistArtist'):
         
        from apps.playlist.services import PlaylistService
        service = PlaylistService()
        
        # データの準備 (モック)
        user = MockUser
        user.email = "test@example.com"
        
        artist = MockArtist
        artist.spotify_id = "4Z8W79mYvSGrv21ZpS0S5v"
        artist.name = "Radiohead"
        
        # 外部サービスをモック化
        service.spotify_service.fetch_get_artist_top_tracks = MagicMock(return_value=[
            {"id": "track1", "name": "Creep"},
            {"id": "track2", "name": "Karma Police"}
        ])
        service.setlist_service.get_latest_setlist_song_names = MagicMock(return_value=["Creep", "No Surprises"])
        service.spotify_service.fetch_search_tracks = MagicMock(side_effect=lambda q, limit: [
            {"id": "track_id_" + q.split(':')[1].split(' ')[0], "name": q.split(':')[1].split(' ')[0]}
        ])
        service.spotify_service.fetch_get_recommendations = MagicMock(return_value=[
            {"id": "rec1", "name": "Fake Plastic Trees"}
        ])

        base_data = {
            "title": "Test Playlist",
            "artist_ids": [artist],
            "get_tracks_count": 2,
            "mood_brightness": 60,
            "mood_intensity": 40
        }

        # パターン検証
        print("--- Testing Patterns ---")
        
        # top_tracks
        base_data["pattern"] = "top_tracks"
        tracks = service.generate_playlist_tracks(datetime.now(), "web", user, base_data)
        print(f"Pattern: top_tracks, Found: {len(tracks)} tracks")
        for t in tracks:
            print(f"  - {t['name']} ({t['spotify_id']})")
        
        assert len(tracks) == 2
        assert tracks[0]["name"] == "Creep"

        # set_list
        base_data["pattern"] = "set_list"
        tracks = service.generate_playlist_tracks(datetime.now(), "web", user, base_data)
        print(f"Pattern: set_list, Found: {len(tracks)} tracks")
        for t in tracks:
            print(f"  - {t['name']} ({t['spotify_id']})")
        
        assert len(tracks) == 2
        assert tracks[1]["name"] == "No" # No Surprises -> No in my mock mapping

        # moodfilter
        base_data["pattern"] = "moodfilter"
        tracks = service.generate_playlist_tracks(datetime.now(), "web", user, base_data)
        print(f"Pattern: moodfilter, Found: {len(tracks)} tracks")
        for t in tracks:
            print(f"  - {t['name']} ({t['spotify_id']})")
        
        assert len(tracks) == 1
        service.spotify_service.fetch_get_recommendations.assert_called_with(
            seed_artists=[artist.spotify_id],
            limit=2,
            target_valence=0.6,
            target_energy=0.4
        )

        print("\nVerification Successful!")

if __name__ == "__main__":
    run_verification()
