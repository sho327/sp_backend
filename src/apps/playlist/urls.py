# coding: utf-8
from django.urls import include, path
from rest_framework import routers

from apps.playlist.views.model_t_playlist import Model_T_PlaylistViewSet

app_name = "playlist"

router = routers.DefaultRouter()
router.register("model-t_playlist", Model_T_PlaylistViewSet, basename="model_t_playlist")

urlpatterns = [
    path("", include(router.urls)),
]
