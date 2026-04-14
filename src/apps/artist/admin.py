# from django.contrib import admin
# from apps.artist.models import M_ArtistTag, M_ArtistContext, T_Artist, R_ArtistTag

# # ------------------------------------------------------------------
# # Inline: アーティストに紐づくタグの編集
# # ------------------------------------------------------------------
# class R_ArtistTagInline(admin.TabularInline):
#     """
#     アーティスト詳細画面からタグを直接追加・削除するための設定
#     """
#     model = R_ArtistTag
#     extra = 1  # デフォルトで表示する空の入力行数
#     fields = ("tag", "created_at")
#     readonly_fields = ("created_at",)

# # ------------------------------------------------------------------
# # M_ArtistTag (アーティストタグマスタ)
# # ------------------------------------------------------------------
# @admin.register(M_ArtistTag)
# class M_ArtistTagAdmin(admin.ModelAdmin):
#     list_display = ("name", "created_at", "deleted_at")
#     search_fields = ("name",)
#     list_filter = ("deleted_at",)
#     ordering = ("name",)

# # ------------------------------------------------------------------
# # M_ArtistContext (アーティストコンテキストマスタ)
# # ------------------------------------------------------------------
# @admin.register(M_ArtistContext)
# class M_ArtistContextAdmin(admin.ModelAdmin):
#     list_display = ("name", "created_at", "deleted_at")
#     search_fields = ("name",)
#     list_filter = ("deleted_at",)
#     ordering = ("name",)

# # ------------------------------------------------------------------
# # T_Artist (アーティストトラン)
# # ------------------------------------------------------------------
# @admin.register(T_Artist)
# class T_ArtistAdmin(admin.ModelAdmin):
#     """
#     ユーザーが登録したアーティスト情報の管理
#     """
#     list_display = ("name", "user", "spotify_id", "context", "created_at")
#     list_filter = ("context", "user", "deleted_at")
#     search_fields = ("name", "spotify_id", "user__user_id_display", "user__display_name")
#     readonly_fields = ("id", "created_at", "updated_at")

#     # 詳細画面でのレイアウト
#     fieldsets = (
#         (None, {"fields": ("id", "user")}),
#         ("Spotify情報", {"fields": ("name", "spotify_id", "spotify_image", "genres")}),
#         ("分類・背景", {"fields": ("context",)}),
#         ("システム情報", {"fields": ("created_method", "updated_method", "created_at", "updated_at", "deleted_at")}),
#     )

#     # アーティスト詳細画面でタグの紐付けを管理可能にする
#     inlines = [R_ArtistTagInline]

# # ------------------------------------------------------------------
# # R_ArtistTag (リレーション) ※単体管理が必要な場合のみ
# # ------------------------------------------------------------------
# @admin.register(R_ArtistTag)
# class R_ArtistTagAdmin(admin.ModelAdmin):
#     list_display = ("artist", "tag", "created_at")
#     search_fields = ("artist__name", "tag__name")
#     readonly_fields = ("created_at", "updated_at")
