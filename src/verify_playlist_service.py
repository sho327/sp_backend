import os
import django
import sys
from unittest.mock import MagicMock
from datetime import datetime

# Django環境のセットアップ
sys.path.append('/Users/shogokato/test/my_sample_stb_zip/src')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.playlist.services import PlaylistService
from apps.artist.models import T_Artist
from apps.account.models import M_User

def run_verification():
    service = PlaylistService()
    
    # 1. データの準備 (モック)
    user, _ = M_User.objects.get_or_create(email="test@example.com")
    artist, _ = T_Artist.objects.get_or_create(
        user=user, 
        spotify_id="4Z8W79mYvSGrv21ZpS0S5v", # Radiohead
        name="Radiohead"
    )
    
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

    # set_list
    base_data["pattern"] = "set_list"
    tracks = service.generate_playlist_tracks(datetime.now(), "web", user, base_data)
    print(f"Pattern: set_list, Found: {len(tracks)} tracks")
    for t in tracks:
        print(f"  - {t['name']} ({t['spotify_id']})")

    # moodfilter
    base_data["pattern"] = "moodfilter"
    tracks = service.generate_playlist_tracks(datetime.now(), "web", user, base_data)
    print(f"Pattern: moodfilter, Found: {len(tracks)} tracks")
    for t in tracks:
        print(f"  - {t['name']} ({t['spotify_id']})")

    # create_playlist 検証
    print("\n--- Testing create_playlist ---")
    base_data["tracks"] = tracks
    playlist = service.create_playlist(datetime.now(), "web", user, base_data)
    print(f"Playlist created: {playlist.title}")
    track_count = playlist.playlist_t_playlist_track_set.count()
    print(f"Tracks in DB: {track_count}")

if __name__ == "__main__":
    run_verification()
