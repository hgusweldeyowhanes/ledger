from django.contrib import admin
from django.utils.html import format_html

from .models import Bookmark, Category, Comment, Post, PostLike, Tag


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "color", "swatch")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)

    @admin.display(description="color")
    def swatch(self, obj):
        return format_html(
            '<span style="display:inline-block;width:1.2rem;height:1.2rem;border-radius:4px;background:{};"></span>',
            obj.color,
        )


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    fields = ("author", "body", "parent", "is_approved", "is_deleted")
    readonly_fields = ("author",)


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "status", "featured", "published_at", "view_count", "reading_time")
    list_filter = ("status", "featured", "categories", "published_at")
    search_fields = ("title", "excerpt", "content")
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("author",)
    filter_horizontal = ("categories", "tags")
    date_hierarchy = "published_at"
    list_editable = ("status", "featured")
    inlines = [CommentInline]
    readonly_fields = ("reading_time", "view_count")
    actions = ("publish_posts", "archive_posts")

    @admin.action(description="Publish selected posts")
    def publish_posts(self, request, queryset):
        queryset.update(status=Post.Status.PUBLISHED)

    @admin.action(description="Archive selected posts")
    def archive_posts(self, request, queryset):
        queryset.update(status=Post.Status.ARCHIVED)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("post", "author", "short_body", "is_approved", "created_at")
    list_filter = ("is_approved", "created_at")
    search_fields = ("body", "author__username", "post__title")
    actions = ("approve_comments",)

    @admin.display(description="body")
    def short_body(self, obj):
        return obj.body[:60]

    @admin.action(description="Approve selected comments")
    def approve_comments(self, request, queryset):
        queryset.update(is_approved=True)


@admin.register(PostLike)
class PostLikeAdmin(admin.ModelAdmin):
    list_display = ("post", "user", "created_at")


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ("post", "user", "created_at")
