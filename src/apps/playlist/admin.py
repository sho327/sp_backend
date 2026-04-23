from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline
from apps.playlist.models import T_Playlist, T_PlaylistTrack, R_PlaylistArtist

# # 共通Mixin
class SaveAdminMixin:
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
            obj.created_method = "admin_panel"
        obj.updated_by = request.user
        obj.updated_method = "admin_panel"
        super().save_model(request, obj, form, change)
    
    # SHOW_VIEW_ON_SITEがTrueの場合だけ設定される
    # def view_on_site(self, obj):
    #     return "http://localhost:3000/dashboard"

class SoftDeleteFilter(admin.SimpleListFilter):
    title = _('状態')
    parameter_name = 'is_deleted'
    def lookups(self, request, model_admin):
        return (('active', _('有効のみ')), ('deleted', _('削除済みのみ')),)
    def queryset(self, request, queryset):
        if self.value() == 'active': return queryset.filter(deleted_at__isnull=True)
        if self.value() == 'deleted': return queryset.filter(deleted_at__isnull=False)
        return queryset

# ------------------------------------------------------------------
# Inlines
# ------------------------------------------------------------------
class T_PlaylistTrackInline(TabularInline):
    model = T_PlaylistTrack
    extra = 0
    fields = ("spotify_name", "spotify_artist_name", "spotify_id")
    readonly_fields = ("spotify_id",)
    show_change_link = True

class R_PlaylistArtistInline(TabularInline):
    model = R_PlaylistArtist
    extra = 0
    autocomplete_fields = ["artist"]

# ------------------------------------------------------------------
# Admins
# ------------------------------------------------------------------

@admin.register(T_Playlist)
class T_PlaylistAdmin(SaveAdminMixin, ModelAdmin):
    list_display = ("title", "user", "created_at", "deleted_at")
    list_filter = (SoftDeleteFilter, "user", "deleted_at")
    search_fields = ("title", "user__user_id_display", "user__display_name")
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = [R_PlaylistArtistInline, T_PlaylistTrackInline]
    
    fieldsets = (
        (None, {"fields": ("id", "user", "title", "image")}),
        ("システム情報", {
            "fields": ("created_method", "updated_method", "created_at", "updated_at", "deleted_at"),
            "classes": ("collapse",)
        }),
    )

@admin.register(T_PlaylistTrack)
class T_PlaylistTrackAdmin(SaveAdminMixin, ModelAdmin):
    list_display = ("spotify_name", "spotify_artist_name", "playlist", "spotify_popularity", "deleted_at")
    list_filter = (SoftDeleteFilter, "playlist", "spotify_album_type")
    search_fields = ("spotify_name", "spotify_artist_name", "spotify_id")
    readonly_fields = ("id", "created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("id", "playlist")}),
        ("Spotify 基本情報", {"fields": ("spotify_id", "spotify_name", "spotify_artist_name", "spotify_isrc")}),
        ("アルバム・メタ情報", {"fields": (
            "spotify_album_id", "spotify_album_name", "spotify_album_type", 
            "spotify_release_date", "spotify_duration_ms", "spotify_popularity"
        )}),
        ("システム情報", {
            "fields": ("created_method", "updated_method", "created_at", "updated_at", "deleted_at"),
            "classes": ("collapse",)
        }),
    )

# @admin.register(R_PlaylistArtist)
# class R_PlaylistArtistAdmin(SaveAdminMixin, ModelAdmin):
#     list_display = ("playlist", "artist", "created_at", "deleted_at")
#     list_filter = (SoftDeleteFilter, "playlist",)
#     autocomplete_fields = ["playlist", "artist"]