from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import (
    AuthorFollow,
    Category,
    Comment,
    NewsletterSubscriber,
    Notification,
    Post,
    PostRevision,
    Series,
    SeriesMembership,
    Tag,
)
from .services import comment_should_auto_approve

User = get_user_model()


class UserPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "first_name", "last_name")


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, style={"input_type": "password"})
    password2 = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = ("username", "email", "password", "password2", "first_name", "last_name")

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password2": "Passwords must match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")
        extra = {}
        if "name" in {f.name for f in User._meta.get_fields()}:
            extra["name"] = validated_data.get("first_name") or validated_data["username"]
        return User.objects.create_user(**validated_data, **extra)


class CategorySerializer(serializers.ModelSerializer):
    post_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ("id", "name", "slug", "description", "color", "post_count")
        read_only_fields = ("slug",)


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ("id", "name", "slug")
        read_only_fields = ("slug",)


class CommentSerializer(serializers.ModelSerializer):
    author = UserPublicSerializer(read_only=True)
    replies = serializers.SerializerMethodField()
    post_title = serializers.CharField(source="post.title", read_only=True)
    post_slug = serializers.CharField(source="post.slug", read_only=True)

    class Meta:
        model = Comment
        fields = (
            "id",
            "post",
            "post_title",
            "post_slug",
            "author",
            "parent",
            "body",
            "is_approved",
            "created_at",
            "replies",
        )
        read_only_fields = ("is_approved", "created_at", "post_title", "post_slug")

    def get_replies(self, obj):
        if obj.parent_id:
            return []
        qs = obj.replies.filter(is_deleted=False, is_approved=True)
        return CommentSerializer(qs, many=True, context=self.context).data

    def validate_parent(self, parent):
        if parent and parent.parent_id:
            raise serializers.ValidationError("Replies can only be one level deep.")
        return parent

    def create(self, validated_data):
        request = self.context["request"]
        post = validated_data["post"]
        validated_data["author"] = request.user
        validated_data["is_approved"] = comment_should_auto_approve(request.user, post)
        return super().create(validated_data)


class SeriesBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Series
        fields = ("id", "title", "slug")


class SeriesMembershipSerializer(serializers.ModelSerializer):
    post_title = serializers.CharField(source="post.title", read_only=True)
    post_slug = serializers.CharField(source="post.slug", read_only=True)

    class Meta:
        model = SeriesMembership
        fields = ("id", "post", "post_title", "post_slug", "position")


class SeriesSerializer(serializers.ModelSerializer):
    author = UserPublicSerializer(read_only=True)
    memberships = SeriesMembershipSerializer(many=True, read_only=True)
    post_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Series
        fields = (
            "id",
            "title",
            "slug",
            "description",
            "author",
            "cover_image",
            "memberships",
            "post_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("slug",)


class SeriesWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Series
        fields = ("title", "description", "cover_image")


class PostListSerializer(serializers.ModelSerializer):
    author = UserPublicSerializer(read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    likes_count = serializers.IntegerField(read_only=True)
    comments_count = serializers.IntegerField(read_only=True)
    url = serializers.HyperlinkedIdentityField(view_name="post-detail", lookup_field="slug")
    series = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = (
            "id",
            "title",
            "slug",
            "excerpt",
            "cover_image",
            "author",
            "categories",
            "tags",
            "status",
            "featured",
            "published_at",
            "reading_time",
            "view_count",
            "likes_count",
            "comments_count",
            "series",
            "url",
        )

    def get_series(self, obj):
        membership = obj.series_membership()
        if not membership:
            return None
        return {
            "id": membership.series_id,
            "title": membership.series.title,
            "slug": membership.series.slug,
            "position": membership.position,
        }


class PostDetailSerializer(PostListSerializer):
    content = serializers.CharField()
    category_ids = serializers.PrimaryKeyRelatedField(
        source="categories",
        many=True,
        queryset=Category.objects.all(),
        write_only=True,
        required=False,
    )
    tag_names = serializers.ListField(
        child=serializers.CharField(max_length=40),
        write_only=True,
        required=False,
    )
    series_id = serializers.PrimaryKeyRelatedField(
        queryset=Series.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )
    series_position = serializers.IntegerField(write_only=True, required=False, min_value=1)
    is_liked = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()

    class Meta(PostListSerializer.Meta):
        fields = PostListSerializer.Meta.fields + (
            "content",
            "allow_comments",
            "meta_title",
            "meta_description",
            "category_ids",
            "tag_names",
            "series_id",
            "series_position",
            "is_liked",
            "is_bookmarked",
            "comments",
        )

    def get_is_liked(self, obj):
        user = self.context["request"].user
        if not user.is_authenticated:
            return False
        return obj.likes.filter(user=user).exists()

    def get_is_bookmarked(self, obj):
        user = self.context["request"].user
        if not user.is_authenticated:
            return False
        return obj.bookmarks.filter(user=user).exists()

    def get_comments(self, obj):
        roots = obj.comments.filter(parent__isnull=True, is_deleted=False, is_approved=True)
        return CommentSerializer(roots, many=True, context=self.context).data

    def _apply_tags(self, post, tag_names):
        if tag_names is None:
            return
        tags = []
        for name in tag_names:
            name = name.strip()
            if not name:
                continue
            tag, _ = Tag.objects.get_or_create(name=name)
            tags.append(tag)
        post.tags.set(tags)

    def _apply_series(self, post, series, position, user):
        SeriesMembership.objects.filter(post=post).delete()
        if series is None:
            return
        if series.author_id != user.pk and not user.is_staff:
            raise serializers.ValidationError({"series_id": "You can only add posts to your own series."})
        position = position or 1
        while SeriesMembership.objects.filter(series=series, position=position).exists():
            position += 1
        SeriesMembership.objects.create(series=series, post=post, position=position)

    def create(self, validated_data):
        tag_names = validated_data.pop("tag_names", None)
        series = validated_data.pop("series_id", None)
        position = validated_data.pop("series_position", None)
        post = super().create(validated_data)
        self._apply_tags(post, tag_names)
        self._apply_series(post, series, position, self.context["request"].user)
        return post

    def update(self, instance, validated_data):
        tag_names = validated_data.pop("tag_names", None)
        series = validated_data.pop("series_id", serializers.empty)
        position = validated_data.pop("series_position", None)
        post = super().update(instance, validated_data)
        self._apply_tags(post, tag_names)
        if series is not serializers.empty:
            self._apply_series(post, series, position, self.context["request"].user)
        return post


class NewsletterSubscribeSerializer(serializers.Serializer):
    email = serializers.EmailField()


class NotificationSerializer(serializers.ModelSerializer):
    actor = UserPublicSerializer(read_only=True)
    post_slug = serializers.CharField(source="post.slug", read_only=True, allow_null=True)
    post_title = serializers.CharField(source="post.title", read_only=True, allow_null=True)

    class Meta:
        model = Notification
        fields = (
            "id",
            "actor",
            "verb",
            "post",
            "post_slug",
            "post_title",
            "comment",
            "is_read",
            "created_at",
        )
        read_only_fields = fields


class AuthorFollowSerializer(serializers.ModelSerializer):
    author = UserPublicSerializer(read_only=True)

    class Meta:
        model = AuthorFollow
        fields = ("id", "author", "created_at")


class PostRevisionSerializer(serializers.ModelSerializer):
    edited_by = UserPublicSerializer(read_only=True)

    class Meta:
        model = PostRevision
        fields = (
            "id",
            "post",
            "edited_by",
            "title",
            "excerpt",
            "content",
            "meta_title",
            "meta_description",
            "snapshot",
            "created_at",
        )
        read_only_fields = fields
