import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.account.tests.factories import UserFactory
from apps.artist.tests.factories import ArtistFactory
from apps.playlist.tests.factories import PlaylistFactory, PlaylistTrackFactory


@pytest.mark.django_db
class TestPlaylistViews:
    @pytest.fixture
    def api_client(self):
        user = UserFactory()
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def test_generate_playlist(self, api_client, mocker):
        profile = api_client.handler._force_user.user_t_profile_set
        artist = ArtistFactory(user=profile)

        mocker.patch(
            "apps.playlist.services.SetlistFmService.get_latest_setlist_song_names",
            return_value=["Song A"],
        )
        mocker.patch(
            "apps.playlist.services.SpotifyService.search_track_uri",
            return_value="spotify:track:aaa",
        )
        mocker.patch(
            "apps.playlist.services.SpotifyService.fetch_top_tracks",
            return_value=["spotify:track:bbb"],
        )
        mocker.patch(
            "apps.playlist.services.SpotifyService.fetch_recommendation_tracks",
            return_value=["spotify:track:ccc"],
        )
        mocker.patch(
            "apps.playlist.services.SpotifyService.fetch_tracks_detail_by_uris",
            return_value=[
                {
                    "uri": "spotify:track:aaa",
                    "name": "Song A",
                    "artists": ["Artist A"],
                    "spotify_id": "aaa",
                    "preview_url": None,
                    "external_url": "https://open.spotify.com/track/aaa",
                }
            ],
        )

        url = reverse("playlist:model_t_playlist-generate")
        response = api_client.post(
            url,
            {
                "title": "My Playlist",
                "artist_ids": [str(artist.id)],
                "image_id": None,
                "use_recent_setlist": True,
                "mood_brightness": 50,
                "mood_intensity": 50,
                "popular_tracks_count": 5,
                "total_tracks": 10,
                "pattern": "balanced",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert "playlist" in response.data
        assert "trackset_urls" in response.data

    def test_list_and_retrieve(self, api_client):
        profile = api_client.handler._force_user.user_t_profile_set
        playlist = PlaylistFactory(user=profile, title="Timeline")
        PlaylistTrackFactory(playlist=playlist, name="Track 1")

        list_url = reverse("playlist:model_t_playlist-list")
        list_res = api_client.get(list_url)
        assert list_res.status_code == status.HTTP_200_OK
        assert len(list_res.data) >= 1

        detail_url = reverse("playlist:model_t_playlist-detail", args=[playlist.id])
        detail_res = api_client.get(detail_url)
        assert detail_res.status_code == status.HTTP_200_OK
        assert detail_res.data["track_count"] == 1

    def test_replace_tracks(self, api_client, mocker):
        profile = api_client.handler._force_user.user_t_profile_set
        playlist = PlaylistFactory(user=profile)
        mocker.patch(
            "apps.playlist.services.SpotifyService.fetch_tracks_detail_by_uris",
            return_value=[
                {
                    "uri": "spotify:track:ttt",
                    "name": "Track T",
                    "artists": ["Artist T"],
                    "spotify_id": "ttt",
                    "preview_url": None,
                    "external_url": "https://open.spotify.com/track/ttt",
                }
            ],
        )
        url = reverse("playlist:model_t_playlist-replace-tracks", args=[playlist.id])
        response = api_client.post(url, {"track_ids": ["ttt"]}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["playlist_id"] == str(playlist.id)
        assert response.data["updated_count"] == 1

    def test_search_tracks(self, api_client, mocker):
        mocker.patch(
            "apps.playlist.services.SpotifyService.search_tracks",
            return_value=[
                {
                    "spotify_id": "abc",
                    "uri": "spotify:track:abc",
                    "name": "My Song",
                    "artists": ["Artist X"],
                    "preview_url": None,
                    "external_url": "https://open.spotify.com/track/abc",
                }
            ],
        )

        url = reverse("playlist:model_t_playlist-search-tracks")
        response = api_client.get(
            url,
            {
                "artist_spotify_id": "artist_1",
                "q": "song",
                "limit": 5,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["spotify_id"] == "abc"

    def test_partial_update_and_delete(self, api_client):
        profile = api_client.handler._force_user.user_t_profile_set
        playlist = PlaylistFactory(user=profile, title="Before")

        detail_url = reverse("playlist:model_t_playlist-detail", args=[playlist.id])
        patch_res = api_client.patch(detail_url, {"title": "After"}, format="json")
        assert patch_res.status_code == status.HTTP_200_OK
        assert patch_res.data["title"] == "After"

        delete_res = api_client.delete(detail_url)
        assert delete_res.status_code == status.HTTP_204_NO_CONTENT

    def test_replace_tracks_validation_error(self, api_client):
        profile = api_client.handler._force_user.user_t_profile_set
        playlist = PlaylistFactory(user=profile)
        url = reverse("playlist:model_t_playlist-replace-tracks", args=[playlist.id])
        response = api_client.post(url, {"track_ids": []}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
