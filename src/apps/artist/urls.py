# coding: utf-8
from django.urls import path, include
from rest_framework import routers

# --- アーティストモジュール ---
from apps.artist.views.master_artist_tag import M_ArtistTagViewSet
from apps.artist.views.master_artist_context import M_ArtistContextViewSet
from apps.artist.views.artist_list import ArtistListView
from apps.artist.views.artist_detail import ArtistDetailView
from apps.artist.views.artist_create import ArtistCreateView
from apps.artist.views.artist_update import ArtistUpdateView
from apps.artist.views.artist_delete import ArtistDeleteView
from apps.artist.views.artist_search import ArtistSearchView

app_name = "artist"

router = routers.DefaultRouter()
router.register("master_tags", M_ArtistTagViewSet, basename='master_artist_tag')
router.register("master_contexts", M_ArtistContextViewSet, basename='master_artist_context')

urlpatterns = [
    # ViewSet関連のURL(CRUD一括)
    path('', include(router.urls)),
    path('list/', ArtistListView.as_view(), name='artist_list'),
    path('create/', ArtistCreateView.as_view(), name='artist_create'),
    path('search/', ArtistSearchView.as_view(), name='artist_search'),
    path('<uuid:artist_id>/', ArtistDetailView.as_view(), name='artist_detail'),
    path('<uuid:artist_id>/update/', ArtistUpdateView.as_view(), name='artist_update'),
    path('<uuid:artist_id>/delete/', ArtistDeleteView.as_view(), name='artist_delete'),
]