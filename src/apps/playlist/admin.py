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
    list_display = ("spotify_name", "display_artist_name", "spotify_artist_name", "playlist", "deleted_at")
    list_filter = (SoftDeleteFilter, "playlist", "spotify_album_type")
    search_fields = ("spotify_name", "display_artist_name", "spotify_artist_name", "spotify_id")
    readonly_fields = ("id", "created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("id", "playlist")}),
        ("Spotify 基本情報", {"fields": (
            "spotify_id", "spotify_name", "display_artist_name", "spotify_artist_id", 
            "spotify_artist_name", "spotify_isrc"
        )}),
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


from django.urls import path
from django.shortcuts import redirect
from django.views.generic import TemplateView
from django.contrib import messages
from unfold.views import UnfoldModelAdminViewMixin
from apps.playlist.forms.track_search import TrackSearchForm
from apps.playlist.services import PlaylistService
from django.utils import timezone
from core.utils.date_format import convert_to_site_timezone
from core.exceptions.exceptions import ApplicationError
# ------------------------------------------------------------------
# カスタムページ(トラック検索)
# ------------------------------------------------------------------
class TrackSearchView(UnfoldModelAdminViewMixin, TemplateView):
    title = "トラック検索"
    permission_required = ()
    template_name = "playlist/track_search.html"
    playlist_service = PlaylistService()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        date_now: datetime = convert_to_site_timezone(timezone.now())
        form = TrackSearchForm(self.request.GET or None)
        results = None

        if form.is_valid():
            data = {
                "search_artist_name" :form.cleaned_data["search_artist_name"],
                "search_track_name" :form.cleaned_data["search_track_name"],
                "limit" :form.cleaned_data["limit"],
            }
            # サービス実行(トラック検索)※SpotifyAPI使用
            results = self.playlist_service.search_tracks(
                date_now=date_now,
                kino_id="track_search_admin",
                user=self.request.user,
                validated_data=data,
            )

        # 検索結果の各トラックに既登録情報を付与
        user_playlists = T_Playlist.objects.filter(user=self.request.user, deleted_at__isnull=True)
        total_playlist_count = user_playlists.count()

        if results:
            tracks_in_playlists = T_PlaylistTrack.objects.filter(
                playlist__in=user_playlists,
                deleted_at__isnull=True
            ).values("spotify_id", "playlist_id")
            
            track_playlist_map = {}
            for item in tracks_in_playlists:
                sid = item["spotify_id"]
                pid = str(item["playlist_id"])
                if sid not in track_playlist_map:
                    track_playlist_map[sid] = []
                track_playlist_map[sid].append(pid)

            for track in results:
                added_ids = track_playlist_map.get(track["spotify_id"], [])
                track["added_playlist_ids"] = added_ids
                # すべてのプレイリストに追加済みか判定
                track["is_fully_added"] = (len(added_ids) >= total_playlist_count) and (total_playlist_count > 0)

        context.update({
            "form": form,
            "results": results,
            "playlists": user_playlists.order_by("-updated_at"),
        })
        return context

    def post(self, request, *args, **kwargs):
        playlist_id = request.POST.get("playlist_id")
        if not playlist_id:
            messages.error(request, "追加先のプレイリストを選択してください。")
            return redirect(request.get_full_path())

        # POSTデータから楽曲情報を抽出
        track_data = {
            "spotify_id": request.POST.get("spotify_id"),
            "spotify_name": request.POST.get("spotify_name"),
            "spotify_artist_id": request.POST.get("spotify_artist_id"),
            "spotify_artist_name": request.POST.get("spotify_artist_name"),
            "display_artist_name": request.POST.get("display_artist_name"),
            "spotify_album_id": request.POST.get("spotify_album_id"),
            "spotify_album_name": request.POST.get("spotify_album_name"),
            "spotify_album_type": request.POST.get("spotify_album_type"),
            "spotify_release_date": request.POST.get("spotify_release_date"),
            "spotify_duration_ms": int(request.POST.get("spotify_duration_ms", 0)) if request.POST.get("spotify_duration_ms") else 0,
            "spotify_popularity": int(request.POST.get("spotify_popularity", 0)) if request.POST.get("spotify_popularity") else 0,
            "spotify_isrc": request.POST.get("spotify_isrc"),
        }

        try:
            date_now = convert_to_site_timezone(timezone.now())
            self.playlist_service.add_playlist_track(
                date_now=date_now,
                kino_id="track_search_admin",
                user=request.user,
                playlist_id=playlist_id,
                validated_data=track_data,
            )
            messages.success(request, f"「{track_data['spotify_name']}」をプレイリストに追加しました。")
        except ApplicationError as e:
            messages.error(request, f"追加に失敗しました: {str(e)}")
        except Exception as e:
            messages.error(request, "予期せぬエラーが発生しました。")

        return redirect(request.get_full_path())
