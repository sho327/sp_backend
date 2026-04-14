from django.contrib import admin

# --- プレイリストモジュール
from apps.playlist.models import T_Playlist, T_PlaylistTrack


@admin.register(T_Playlist)
class T_PlaylistAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "spotify_id", "created_at", "deleted_at")
    list_filter = ("deleted_at", "created_at")
    search_fields = ("title", "spotify_id", "user__user_id_display", "user__display_name")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(T_PlaylistTrack)
class T_PlaylistTrackAdmin(admin.ModelAdmin):
    list_display = ("name", "playlist", "artist", "spotify_id", "created_at", "deleted_at")
    list_filter = ("deleted_at", "created_at")
    search_fields = ("name", "spotify_id", "artist__name", "playlist__title")
    readonly_fields = ("id", "created_at", "updated_at")
