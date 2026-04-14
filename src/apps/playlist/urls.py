# coding: utf-8
from django.urls import path, include
from rest_framework import routers

# --- プレイリストモジュール ---
from apps.playlist.views.playlist_list import PlaylistListView
from apps.playlist.views.playlist_detail import PlaylistDetailView
from apps.playlist.views.playlist_delete import PlaylistDeleteView
from apps.playlist.views.playlist_generate import PlaylistGenerateView
from apps.playlist.views.playlist_create import PlaylistCreateView

app_name = "playlist"

router = routers.DefaultRouter()

urlpatterns = [
    # ViewSet関連のURL(CRUD一括)
    path('', include(router.urls)),
    path('list/', PlaylistListView.as_view(), name='playlist_list'),
    path('generate/', PlaylistGenerateView.as_view(), name='playlist_generate'),
    path('create/', PlaylistCreateView.as_view(), name='playlist_create'),
    path('<uuid:playlist_id>/', PlaylistDetailView.as_view(), name='playlist_detail'),
    path('<uuid:playlist_id>/delete/', PlaylistDeleteView.as_view(), name='playlist_delete'),
]