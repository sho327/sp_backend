from django.contrib import admin
from django.utils.translation import gettext_lazy as _

# --- プレイリストモジュール ---
from apps.playlist.models import T_Playlist, T_PlaylistTrack, R_PlaylistArtist

class SoftDeleteFilter(admin.SimpleListFilter):
    title = _('状態')
    parameter_name = 'is_deleted'

    def lookups(self, request, model_admin):
        return (
            ('active', _('有効のみ')),
            ('deleted', _('削除済みのみ')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'active':
            return queryset.filter(deleted_at__isnull=True)
        if self.value() == 'deleted':
            return queryset.filter(deleted_at__isnull=False)
        return queryset

# ------------------------------------------------------------------
# Inlines (プレイリスト詳細画面に埋め込むパーツ)
# ------------------------------------------------------------------

class T_PlaylistTrackInline(admin.TabularInline):
    """プレイリスト内のトラック編集用"""
    model = T_PlaylistTrack
    extra = 0
    fields = ("spotify_name", "spotify_artist_name", "spotify_id")
    readonly_fields = ("spotify_id",) # 編集画面でIDを触らせない場合
    show_change_link = True           # 詳細画面へ飛べるようにする

class R_PlaylistArtistInline(admin.TabularInline):
    """プレイリストのアーティスト紐付け編集用"""
    model = R_PlaylistArtist
    extra = 0
    autocomplete_fields = ["artist"] # 検索しやすくする

# ------------------------------------------------------------------
# Admins
# ------------------------------------------------------------------

@admin.register(T_Playlist)
class T_PlaylistAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "created_at", "deleted_at")
    list_filter = (SoftDeleteFilter, "user", "deleted_at")
    search_fields = ("title", "user__user_id_display", "user__display_name")
    readonly_fields = ("id", "created_at", "updated_at")
    
    fieldsets = (
        (None, {"fields": ("id", "user", "title", "image")}),
        ("システム情報", {
            "fields": ("created_method", "updated_method", "created_at", "updated_at", "deleted_at"),
            "classes": ("collapse",)
        }),
    )
    
    # プレイリスト画面からトラックとアーティストを直接管理
    inlines = [R_PlaylistArtistInline, T_PlaylistTrackInline]

    def save_model(self, request, obj, form, change):
        # 新規作成時 (change=False)
        if not change:
            # if not obj.updated_by:
            #     obj.updated_by = request.user
            # if not obj.updated_method:
            #     obj.updated_method = "admin_panel"
            
            # admin新規時は以下とする
            obj.created_by = request.user
            obj.created_method = "admin_panel"
            obj.updated_by = request.user
            obj.updated_method = "admin_panel"
        
        # 更新時(change=True)
        else:
            # 「更新時」は既存の値が入っているので、「手動でクリアされて空になった場合」や「意図的に上書きしたい場合」を考える必要がある
            # 基本的に「Adminで誰かが保存した」というログなら、強制的に上書きしても良いケースが多い？
            # ※「空の場合だけ自動セット」にしたいなら以下のようにする
            # if not obj.updated_by:
            #     obj.updated_by = request.user
            # if not obj.updated_method:
            #     obj.updated_method = "admin_panel"
            
            # admin更新時は以下とする
            obj.updated_by = request.user
            obj.updated_method = "admin_panel"
        
        super().save_model(request, obj, form, change)


@admin.register(T_PlaylistTrack)
class T_PlaylistTrackAdmin(admin.ModelAdmin):
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

    def save_model(self, request, obj, form, change):
        # 新規作成時 (change=False)
        if not change:
            # if not obj.updated_by:
            #     obj.updated_by = request.user
            # if not obj.updated_method:
            #     obj.updated_method = "admin_panel"
            
            # admin新規時は以下とする
            obj.created_by = request.user
            obj.created_method = "admin_panel"
            obj.updated_by = request.user
            obj.updated_method = "admin_panel"
        
        # 更新時(change=True)
        else:
            # 「更新時」は既存の値が入っているので、「手動でクリアされて空になった場合」や「意図的に上書きしたい場合」を考える必要がある
            # 基本的に「Adminで誰かが保存した」というログなら、強制的に上書きしても良いケースが多い？
            # ※「空の場合だけ自動セット」にしたいなら以下のようにする
            # if not obj.updated_by:
            #     obj.updated_by = request.user
            # if not obj.updated_method:
            #     obj.updated_method = "admin_panel"
            
            # admin更新時は以下とする
            obj.updated_by = request.user
            obj.updated_method = "admin_panel"
        
        super().save_model(request, obj, form, change)


@admin.register(R_PlaylistArtist)
class R_PlaylistArtistAdmin(admin.ModelAdmin):
    list_display = ("playlist", "artist", "created_at", "deleted_at")
    list_filter = (SoftDeleteFilter, "playlist",)
    autocomplete_fields = ["playlist", "artist"] # プレイリストやアーティストが多い場合に有効

    def save_model(self, request, obj, form, change):
        # 新規作成時 (change=False)
        if not change:
            # if not obj.updated_by:
            #     obj.updated_by = request.user
            # if not obj.updated_method:
            #     obj.updated_method = "admin_panel"
            
            # admin新規時は以下とする
            obj.created_by = request.user
            obj.created_method = "admin_panel"
            obj.updated_by = request.user
            obj.updated_method = "admin_panel"
        
        # 更新時(change=True)
        else:
            # 「更新時」は既存の値が入っているので、「手動でクリアされて空になった場合」や「意図的に上書きしたい場合」を考える必要がある
            # 基本的に「Adminで誰かが保存した」というログなら、強制的に上書きしても良いケースが多い？
            # ※「空の場合だけ自動セット」にしたいなら以下のようにする
            # if not obj.updated_by:
            #     obj.updated_by = request.user
            # if not obj.updated_method:
            #     obj.updated_method = "admin_panel"
            
            # admin更新時は以下とする
            obj.updated_by = request.user
            obj.updated_method = "admin_panel"
        
        super().save_model(request, obj, form, change)