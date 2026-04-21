from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from apps.artist.models import M_ArtistTag, M_ArtistContext, T_Artist, R_ArtistTag

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
# Inline: アーティストに紐づくタグの編集
# ------------------------------------------------------------------
class R_ArtistTagInline(admin.TabularInline):
    """
    アーティスト詳細画面からタグを直接追加・削除するための設定
    """
    model = R_ArtistTag
    extra = 1  # デフォルトで表示する空の入力行数
    fields = ("tag", "created_at")
    readonly_fields = ("created_at",)

# ------------------------------------------------------------------
# M_ArtistTag (アーティストタグマスタ)
# ------------------------------------------------------------------
@admin.register(M_ArtistTag)
class M_ArtistTagAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at", "deleted_at")
    search_fields = ("name",)
    list_filter = (SoftDeleteFilter, "deleted_at",)
    ordering = ("name",)

    # def get_queryset(self, request):
    #     # 元のクエリセットに対してフィルタを掛ける
    #     return super().get_queryset(request).filter(deleted_at__isnull=True)

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

# ------------------------------------------------------------------
# M_ArtistContext (アーティストコンテキストマスタ)
# ------------------------------------------------------------------
@admin.register(M_ArtistContext)
class M_ArtistContextAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at", "deleted_at")
    search_fields = ("name",)
    list_filter = (SoftDeleteFilter, "deleted_at",)
    ordering = ("name",)

    # def get_queryset(self, request):
    #     # 元のクエリセットに対してフィルタを掛ける
    #     return super().get_queryset(request).filter(deleted_at__isnull=True)

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

# ------------------------------------------------------------------
# T_Artist (アーティストトラン)
# ------------------------------------------------------------------
@admin.register(T_Artist)
class T_ArtistAdmin(admin.ModelAdmin):
    """
    ユーザーが登録したアーティスト情報の管理
    """
    # 一覧表示の設定
    list_display = ("name", "user", "deezer_id", "context", "created_at", "deleted_at")
    list_filter = (SoftDeleteFilter, "context", "user", "deleted_at")
    
    # 検索設定
    search_fields = ("name", "deezer_id", "user__user_id_display", "user__display_name")
    
    # 編集不可フィールド
    readonly_fields = ("id", "created_at", "updated_at")

    # 詳細画面でのレイアウト
    fieldsets = (
        (None, {"fields": ("id", "user")}),
        ("基本情報", {"fields": ("name", "deezer_id", "deezer_image")}),
        ("SetlistFm連携情報", {"fields": ("setlistfm_mbid", "is_mbid_autoset")}),
        ("分類・背景", {"fields": ("context",)}),
        ("システム情報", {
            "fields": ("created_method", "updated_method", "created_at", "updated_at", "deleted_at"),
            "classes": ("collapse",) # 折りたたみ可能にすると見やすくなる
        }),
    )

    # アーティスト詳細画面でタグの紐付けを管理可能にする
    # throughモデル(R_ArtistTag)を使用しているため、インラインで管理するのがベストです
    inlines = [R_ArtistTagInline]

    # def get_queryset(self, request):
    #     # 元のクエリセットに対してフィルタを掛ける
    #     return super().get_queryset(request).filter(deleted_at__isnull=True)

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

# ------------------------------------------------------------------
# R_ArtistTag(リレーション)※単体管理が必要な場合のみ
# ------------------------------------------------------------------
@admin.register(R_ArtistTag)
class R_ArtistTagAdmin(admin.ModelAdmin):
    list_display = ("artist", "tag", "created_at")
    list_filter = (SoftDeleteFilter, )
    search_fields = ("artist__name", "tag__name")
    readonly_fields = ("created_at", "updated_at")

    # def get_queryset(self, request):
    #     # 元のクエリセットに対してフィルタを掛ける
    #     return super().get_queryset(request).filter(deleted_at__isnull=True)

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
