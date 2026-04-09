# coding: utf-8
from django.urls import path, include
from rest_framework import routers

from apps.artist.views.model_m_artist_tag import Model_M_ArtistTagViewSet
from apps.artist.views.model_m_artist_context import Model_M_ArtistContextViewSet
from apps.artist.views.model_t_artist import Model_T_ArtistViewSet

app_name = "artist"

router = routers.DefaultRouter()
router.register("model-m_artist_tags", Model_M_ArtistTagViewSet, basename='model_m_artist_tag')
router.register("model-m_artist_contexts", Model_M_ArtistContextViewSet, basename='model_m_artist_context')
router.register("model-t_artist", Model_T_ArtistViewSet, basename='model_t_artist')

urlpatterns = [
    path('', include(router.urls)),
]