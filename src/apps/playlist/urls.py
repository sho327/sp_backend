# coding: utf-8
from django.urls import path, include
from rest_framework import routers

# --- プレイリストモジュール ---
from apps.playlist.views.playlist_list import PlaylistListView
from apps.playlist.views.playlist_detail import PlaylistDetailView
from apps.playlist.views.playlist_delete import PlaylistDeleteView
from apps.playlist.views.playlist_create import PlaylistCreateView
from apps.playlist.views.playlist_update import PlaylistUpdateView

from apps.playlist.views.tracks_generate import TracksGenerateView
from apps.playlist.views.tracks_search import TracksSearchView

from apps.playlist.views.playlist_track_add import PlaylistTrackAddView
from apps.playlist.views.playlist_track_remove import PlaylistTrackRemoveView

app_name = "playlist"

router = routers.DefaultRouter()

urlpatterns = [
    # ViewSet関連のURL(CRUD一括)
    path('', include(router.urls)),
    path('list/', PlaylistListView.as_view(), name='playlist_list'),
    path('create/', PlaylistCreateView.as_view(), name='playlist_create'),
    path('<uuid:playlist_id>/', PlaylistDetailView.as_view(), name='playlist_detail'),
    path('<uuid:playlist_id>/update/', PlaylistUpdateView.as_view(), name='playlist_update'),
    path('<uuid:playlist_id>/delete/', PlaylistDeleteView.as_view(), name='playlist_delete'),

    path('tracks_generate/', TracksGenerateView.as_view(), name='tracks_generate'),
    path('tracks_search/', TracksSearchView.as_view(), name='tracks_search'),

    path('<uuid:playlist_id>/tracks/add/', PlaylistTrackAddView.as_view(), name='playlist_track_add'),
    path('<uuid:playlist_id>/tracks/<uuid:track_id>/remove/', PlaylistTrackRemoveView.as_view(), name='playlist_track_remove'),
]