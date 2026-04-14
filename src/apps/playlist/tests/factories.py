import factory

# --- アカウントモジュール ---
from apps.account.tests.factories import UserFactory

# --- アーティストモジュール
from apps.artist.tests.factories import ArtistFactory

# --- プレイリストモジュール
from apps.playlist.models import T_Playlist, T_PlaylistTrack


class PlaylistFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = T_Playlist

    user = factory.LazyAttribute(lambda o: UserFactory().user_t_profile_set)
    title = factory.Sequence(lambda n: f"Playlist {n}")
    spotify_id = factory.Sequence(lambda n: f"playlist_sp_{n}")


class PlaylistTrackFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = T_PlaylistTrack

    playlist = factory.SubFactory(PlaylistFactory)
    artist = factory.SubFactory(ArtistFactory)
    name = factory.Sequence(lambda n: f"Track {n}")
    spotify_id = factory.Sequence(lambda n: f"track_sp_{n}")
